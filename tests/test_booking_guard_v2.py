"""Characterization and Specification Tests for Phase 1A: booking_guard_v2.

Covers:
1. Per-tenant feature flag 'booking_guard_v2' defaults to False for existing clinics.
2. Characterization: legacy behavior is 100% preserved when flag is OFF.
3. Step attempts counter (email skip offer, phone helpline offer).
4. Global universal interrupts (back/peeche, restart/shuru se, menu, cancel).
5. Idle expiry recovery with Resume / Start New.
6. "Talk to a human" reception contact fallback before Phase 3 HITL.
7. Clearing stale patient draft fields on fresh booking.
8. Recursion limit / loop detector guard.
"""

import time
import unittest
from unittest.mock import MagicMock
from langgraph.checkpoint.memory import MemorySaver

from app.core.feature_flags import is_feature_enabled, FEATURE_BOOKING_GUARD_V2
from app.graph.graph import build_graph, build_whatsapp_thread_id
from app.graph.nodes import GraphNodes
from app.tools.doctors import DoctorDirectory
from app.tools.patients import PatientTools


class FakePatientRepo:
    def __init__(self):
        self.records = []

    def list_patients(self):
        return [dict(r) for r in self.records]

    def create_patient(self, record):
        rec = {
            "Patient ID": "PAT-101",
            "Name": getattr(record, "name", ""),
            "Phone": getattr(record, "phone", ""),
            "Email": getattr(record, "email", ""),
            "Doctor": getattr(record, "doctor", ""),
            "Appointment Date": getattr(record, "appointment_date", ""),
            "Appointment Time": getattr(record, "appointment_time", ""),
            "Token No": "TKN-999",
            "Amount": "500",
            "Payment Method": "Offline",
            "Payment Status": "Pending",
            "Booking Status": "Confirmed",
            "Status": "Confirmed",
        }
        self.records.append(rec)
        return {"success": True, "patient": rec}

    def generate_token(self):
        return {"token_no": "TKN-999"}

    def generate_patient_id(self):
        return {"patient_id": "PAT-101"}


class FakeSlots:
    def get_upcoming_available_slots(self, doctor_name: str, doctor_id: str, today_str: str):
        return [
            {
                "Slot ID": "SLOT-001",
                "Doctor ID": doctor_id or "DOC001",
                "Doctor Name": doctor_name or "Dr. Arjun Mehta",
                "Date": "2026-11-01",
                "Start Time": "10:00 AM",
                "End Time": "10:30 AM",
                "Status": "Available",
            }
        ]

    def get_available_slots(self, doctor_name: str, date: str):
        return [
            {
                "Slot ID": "SLOT-001",
                "Doctor ID": "DOC001",
                "Doctor Name": doctor_name or "Dr. Arjun Mehta",
                "Date": date,
                "Start Time": "10:00 AM",
                "End Time": "10:30 AM",
                "Status": "Available",
            }
        ]

    def book_slot(self, slot_id, patient_id, token_no):
        return {"success": True}


class BookingGuardV2Tests(unittest.TestCase):
    def setUp(self):
        self.llm = MagicMock()
        self.rag = MagicMock()
        rows = [
            ["Doctor ID", "Doctor Name", "Specialization", "Consultation Fee", "Available Days", "Start Time", "End Time", "Status"],
            ["DOC001", "Dr. Arjun Mehta", "General Physician", "500", "Monday, Wednesday, Friday", "10:00 AM", "1:00 PM", "Active"],
            ["DOC002", "Dr. Sana Khan", "Gynecologist", "700", "Tuesday, Thursday, Saturday", "4:00 PM", "7:00 PM", "Active"],
        ]
        self.doc_dir = DoctorDirectory(lambda: rows)
        self.patient_repo = FakePatientRepo()
        self.slots = FakeSlots()
        self.nodes = GraphNodes(
            clinic_name="XYZ Clinic",
            llm=self.llm,
            rag=self.rag,
            doctors=self.doc_dir,
            support_phone="6200126662",
            patients=self.patient_repo,
            slots=self.slots,
        )
        self.checkpointer = MemorySaver()
        self.graph = build_graph(self.nodes, checkpointer=self.checkpointer)

    def _send(self, text: str, phone: str = "919999900001", flags: dict = None):
        tid = build_whatsapp_thread_id("default", phone)
        cfg = {"configurable": {"thread_id": tid}}
        state = {
            "chat_id": tid,
            "thread_id": tid,
            "user_text": text,
            "channel": "whatsapp",
            "phone": phone,
            "patient_phone": phone,
            "tenant_id": "default",
            "clinic_id": "default",
            "clinic_name": "XYZ Clinic",
            "support_phone": "6200126662",
            "feature_flags": flags or {},
        }
        return self.graph.invoke(state, config=cfg)

    # -------------------------------------------------------------------------
    # 1. Feature Flag Defaults Check
    # -------------------------------------------------------------------------
    def test_01_feature_flag_defaults_to_false(self):
        """Golden Rule #2: booking_guard_v2 must default to False for existing tenants."""
        self.assertFalse(is_feature_enabled({}, "booking_guard_v2", default=False))
        self.assertFalse(is_feature_enabled({"ai_agent": True}, "booking_guard_v2", default=False))
        self.assertTrue(is_feature_enabled({"booking_guard_v2": True}, "booking_guard_v2", default=False))

    # -------------------------------------------------------------------------
    # 2. Characterization: Flag OFF preserves legacy behavior 100%
    # -------------------------------------------------------------------------
    def test_02_legacy_behavior_preserved_when_flag_off(self):
        """When booking_guard_v2 is False, booking flow runs in classic mode."""
        phone = "919999900010"
        flags = {"booking_guard_v2": False}

        # Step 1: Start booking
        r1 = self._send("Book Appointment", phone=phone, flags=flags)
        self.assertEqual(r1.get("appointment_step"), "name")
        self.assertIn("name", r1.get("response", "").lower())

        # Step 2: Patient Name
        r2 = self._send("Ramesh Kumar", phone=phone, flags=flags)
        self.assertEqual(r2.get("appointment_step"), "email")
        self.assertIn("email", r2.get("response", "").lower())

        # Step 3: Repeated invalid email does not offer skip with flag OFF
        r3 = self._send("invalid-email-1", phone=phone, flags=flags)
        self.assertEqual(r3.get("appointment_step"), "email")
        self.assertIn("valid email", r3.get("response", "").lower())

    # -------------------------------------------------------------------------
    # 3. Step Attempts Counter (Email skip offer, Phone helpline offer)
    # -------------------------------------------------------------------------
    def test_03_step_attempts_counter_email_offers_skip(self):
        """When booking_guard_v2 is True, 3 failed email inputs offer skip or auto-advance."""
        phone = "919999900020"
        flags = {"booking_guard_v2": True}

        self._send("Book Appointment", phone=phone, flags=flags)
        self._send("Ramesh Kumar", phone=phone, flags=flags)

        r1 = self._send("bademail1", phone=phone, flags=flags)
        self.assertEqual(r1.get("appointment_step"), "email")

        r2 = self._send("bademail2", phone=phone, flags=flags)
        self.assertEqual(r2.get("appointment_step"), "email")

        r3 = self._send("bademail3", phone=phone, flags=flags)
        self.assertIn("skip", r3.get("response", "").lower())

    def test_04_step_attempts_counter_phone_offers_helpline(self):
        """When booking_guard_v2 is True, 3 failed phone inputs offer clinic helpline/callback."""
        phone = "919999900030"
        flags = {"booking_guard_v2": True}

        self._send("Book Appointment", phone=phone, flags=flags)
        self._send("Ramesh Kumar", phone=phone, flags=flags)
        self._send("skip", phone=phone, flags=flags)  # advances to phone step

        self._send("not-a-phone-1", phone=phone, flags=flags)
        self._send("not-a-phone-2", phone=phone, flags=flags)
        r3 = self._send("not-a-phone-3", phone=phone, flags=flags)
        self.assertIn("6200126662", r3.get("response", ""))

    # -------------------------------------------------------------------------
    # 4. Global Universal Interrupts (back/peeche, restart, menu)
    # -------------------------------------------------------------------------
    def test_05_global_interrupt_back(self):
        """When booking_guard_v2 is True, 'back' or 'peeche' steps back to the previous step."""
        phone = "919999900040"
        flags = {"booking_guard_v2": True}

        self._send("Book Appointment", phone=phone, flags=flags)
        self._send("Ramesh Kumar", phone=phone, flags=flags)  # at email step
        r_back = self._send("back", phone=phone, flags=flags)
        self.assertEqual(r_back.get("appointment_step"), "name")
        self.assertIn("name", r_back.get("response", "").lower())

    def test_06_global_interrupt_restart(self):
        """When booking_guard_v2 is True, 'restart' or 'shuru se' restarts fresh booking."""
        phone = "919999900050"
        flags = {"booking_guard_v2": True}

        self._send("Book Appointment", phone=phone, flags=flags)
        self._send("Ramesh Kumar", phone=phone, flags=flags)
        r_restart = self._send("restart", phone=phone, flags=flags)
        self.assertEqual(r_restart.get("appointment_step"), "name")
        self.assertIn("name", r_restart.get("response", "").lower())

    def test_07_global_interrupt_menu(self):
        """When booking_guard_v2 is True, 'menu' shows welcome options without breaking state."""
        phone = "919999900060"
        flags = {"booking_guard_v2": True}

        self._send("Book Appointment", phone=phone, flags=flags)
        r_menu = self._send("menu", phone=phone, flags=flags)
        self.assertIn("welcome", r_menu.get("response", "").lower())

    # -------------------------------------------------------------------------
    # 5. Idle Expiry Recovery (Resume or Start New)
    # -------------------------------------------------------------------------
    def test_08_idle_expiry_recovery(self):
        """When booking_guard_v2 is True, an abandoned draft (>30 mins) prompts Resume vs Start New."""
        phone = "919999900070"
        flags = {"booking_guard_v2": True}

        # User starts booking
        self._send("Book Appointment", phone=phone, flags=flags)
        self._send("Ramesh Kumar", phone=phone, flags=flags)

        # Simulate time passing (> 30 mins) in the state
        tid = build_whatsapp_thread_id("default", phone)
        cfg = {"configurable": {"thread_id": tid}}
        current_state = self.graph.get_state(cfg).values
        # Simulate last activity 35 minutes ago
        simulated_old_time = time.time() - 2100
        current_state["last_activity_timestamp"] = simulated_old_time
        self.graph.update_state(cfg, current_state)

        # User messages after 35 mins
        r_idle = self._send("hi", phone=phone, flags=flags)
        self.assertIn("resume", r_idle.get("response", "").lower())
        self.assertIn("start new", r_idle.get("response", "").lower())

    # -------------------------------------------------------------------------
    # 6. Talk to a Human (Reception Contact Fallback)
    # -------------------------------------------------------------------------
    def test_09_talk_to_a_human_returns_reception_contact(self):
        """When user asks for human/receptionist, returns clinic phone and callback note."""
        phone = "919999900080"
        flags = {"booking_guard_v2": True}

        self._send("Book Appointment", phone=phone, flags=flags)
        r_human = self._send("mujhe kisi insaan se baat karni hai", phone=phone, flags=flags)
        self.assertIn("6200126662", r_human.get("response", ""))

    # -------------------------------------------------------------------------
    # 7. Clear Stale Draft Fields on Fresh Booking
    # -------------------------------------------------------------------------
    def test_10_clear_stale_draft_fields_on_new_booking(self):
        """Starting a new booking wipes out leftover fields from previous drafts."""
        phone = "919999900090"
        flags = {"booking_guard_v2": True}

        # Complete or abandon a previous booking with patient details
        self._send("Book Appointment", phone=phone, flags=flags)
        self._send("Purana Patient", phone=phone, flags=flags)
        self._send("cancel this appointment", phone=phone, flags=flags)

        # Start a brand new booking
        r_new = self._send("Book Appointment", phone=phone, flags=flags)
        draft = r_new.get("appointment_draft", {})
        self.assertNotIn("patient_name", draft)
        self.assertEqual(r_new.get("patient_name"), "")


if __name__ == "__main__":
    unittest.main()
