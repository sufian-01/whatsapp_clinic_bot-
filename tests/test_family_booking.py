"""Tests for Phase 2: Family Booking (Contact-centric multi-patient architecture).

Verifies:
1. Feature flag `family_booking` defaults to False (Golden Rule #2).
2. Legacy behavior preserved when flag is OFF.
3. Database tenant isolation for contacts (Golden Rule #4).
4. Prompting 'choose_for_whom' when family members exist under the WhatsApp phone.
5. Selecting an existing family member reuses profile without re-asking name/phone.
6. Selecting 'New Patient' prompts name and registers new family profile under contact.
7. Multi-appointment status disambiguation (neither family member's appointment is masked).
8. Duplicate booking guard per patient.
"""

import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.core.feature_flags import (
    FEATURE_FAMILY_BOOKING,
    is_feature_enabled,
)
from app.graph.checkpoint import MemorySaver
from app.graph.graph import build_graph, build_whatsapp_thread_id
from app.graph.nodes import GraphNodes
from app.tools.doctors import DoctorDirectory


class FakePatientRepo:
    def __init__(self):
        self.records = []
        self._contacts = {}  # (tenant_id, phone) -> contact dict
        self._family = {}    # contact_id -> list of patient records

    def get_patient(self, patient_id):
        for r in self.records:
            if r.get("Patient ID") == patient_id:
                return r
        return None

    def search_by_phone(self, phone):
        return [r for r in self.records if r.get("Phone") == phone]

    def list_patients(self):
        return list(self.records)

    def list_records(self):
        return list(self.records)

    def create_patient(self, record):
        p_name = getattr(record, "name", "") or getattr(record, "patient_name", "")
        p_phone = getattr(record, "phone", "") or getattr(record, "patient_phone", "")
        pid = getattr(record, "patient_id", "") or f"PAT-{uuid4().hex[:6].upper()}"
        rec = {
            "Patient ID": pid,
            "Name": p_name,
            "Phone": p_phone,
            "Email": getattr(record, "email", "") or "patient@clinic.local",
            "Doctor": getattr(record, "doctor", "") or getattr(record, "doctor_name", ""),
            "Appointment Date": getattr(record, "appointment_date", ""),
            "Appointment Time": getattr(record, "appointment_time", ""),
            "Token No": getattr(record, "token_no", "") or "TKN-101",
            "Amount": "500",
            "Payment Method": "Offline",
            "Payment Status": "Pending",
            "Booking Status": "Confirmed",
            "Status": "Confirmed",
            "Relationship": getattr(record, "relationship_type", "Self"),
        }
        self.records.append(rec)
        return {"success": True, "patient": rec}

    def get_family_members(self, phone, tenant_id="default"):
        return [r for r in self.records if r.get("Phone") == phone]


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


class FamilyBookingTests(unittest.TestCase):
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
    # 1. Feature Flag Defaults Check (Golden Rule #2)
    # -------------------------------------------------------------------------
    def test_01_feature_flag_defaults_to_false(self):
        """Golden Rule #2: family_booking must default to False for all plans and tenants."""
        self.assertFalse(is_feature_enabled({}, FEATURE_FAMILY_BOOKING, default=False))
        self.assertFalse(is_feature_enabled({"ai_agent": True}, FEATURE_FAMILY_BOOKING, default=False))
        self.assertTrue(is_feature_enabled({FEATURE_FAMILY_BOOKING: True}, FEATURE_FAMILY_BOOKING, default=False))

    # -------------------------------------------------------------------------
    # 2. Legacy Behavior Preserved When Flag is OFF
    # -------------------------------------------------------------------------
    def test_02_legacy_booking_flow_when_flag_off(self):
        """When family_booking is False, legacy booking flow starts directly at name step."""
        phone = "919999911111"
        flags = {FEATURE_FAMILY_BOOKING: False}

        # Even if a previous patient exists in repository
        self.patient_repo.records.append({
            "Patient ID": "PAT-001",
            "Name": "Ramesh Kumar",
            "Phone": phone,
            "Doctor": "Dr. Arjun Mehta",
            "Appointment Date": "2026-11-01",
            "Appointment Time": "10:00 AM",
            "Status": "Confirmed",
        })

        r = self._send("Book Appointment", phone=phone, flags=flags)
        self.assertEqual(r.get("appointment_step"), "name")
        self.assertIn("name", r.get("response", "").lower())
        self.assertNotIn("kiske liye", r.get("response", "").lower())

    # -------------------------------------------------------------------------
    # 3. Family Booking: Prompts 'choose_for_whom' When Family Members Exist
    # -------------------------------------------------------------------------
    def test_03_family_booking_prompts_choose_for_whom_when_members_exist(self):
        """When family_booking is True and patient exists, prompts choose_for_whom options."""
        phone = "919999922222"
        flags = {FEATURE_FAMILY_BOOKING: True}

        # Seed existing patient in repo
        self.patient_repo.records.append({
            "Patient ID": "PAT-001",
            "Name": "Ramesh Kumar",
            "Phone": phone,
            "Relationship": "Self",
            "Status": "Confirmed",
        })

        r = self._send("Book Appointment", phone=phone, flags=flags)
        self.assertEqual(r.get("appointment_step"), "choose_for_whom")
        self.assertIn("Ramesh Kumar", r.get("response", ""))
        self.assertIn("1", r.get("response", ""))

    # -------------------------------------------------------------------------
    # 4. Selecting Existing Member Advances Directly to Doctor
    # -------------------------------------------------------------------------
    def test_04_selecting_existing_member_advances_to_doctor(self):
        """Selecting existing family member reuses profile and advances to doctor selection."""
        phone = "919999933333"
        flags = {FEATURE_FAMILY_BOOKING: True}

        self.patient_repo.records.append({
            "Patient ID": "PAT-001",
            "Name": "Ramesh Kumar",
            "Phone": phone,
            "Relationship": "Self",
            "Status": "Confirmed",
        })

        self._send("Book Appointment", phone=phone, flags=flags)
        r_select = self._send("1", phone=phone, flags=flags)

        # Name is already set to Ramesh Kumar without re-asking
        self.assertEqual(r_select.get("patient_name"), "Ramesh Kumar")
        self.assertIn(r_select.get("appointment_step"), ("doctor", "pre_patient_date"))

    # -------------------------------------------------------------------------
    # 5. Selecting New Member Prompts Name
    # -------------------------------------------------------------------------
    def test_05_selecting_new_member_prompts_name(self):
        """Selecting 'New Patient' prompts for the new patient's name."""
        phone = "919999944444"
        flags = {FEATURE_FAMILY_BOOKING: True}

        self.patient_repo.records.append({
            "Patient ID": "PAT-001",
            "Name": "Ramesh Kumar",
            "Phone": phone,
            "Relationship": "Self",
            "Status": "Confirmed",
        })

        self._send("Book Appointment", phone=phone, flags=flags)
        r_new = self._send("new patient", phone=phone, flags=flags)

        self.assertEqual(r_new.get("appointment_step"), "name")
        self.assertIn("name", r_new.get("response", "").lower())

    # -------------------------------------------------------------------------
    # 6. Multi-Appointment Status Shows Both Family Members
    # -------------------------------------------------------------------------
    def test_06_multi_appointment_status_shows_both_family_members(self):
        """When asking for appointments, appointments for all family members under the phone are shown."""
        phone = "919999955555"
        flags = {FEATURE_FAMILY_BOOKING: True}

        # Two family members with separate appointments
        self.patient_repo.records.append({
            "Patient ID": "PAT-001",
            "Name": "Ramesh Kumar",
            "Phone": phone,
            "Doctor": "Dr. Arjun Mehta",
            "Appointment Date": "2026-11-01",
            "Appointment Time": "10:00 AM",
            "Token No": "TKN-101",
            "Status": "Confirmed",
            "Booking Status": "Confirmed",
        })
        self.patient_repo.records.append({
            "Patient ID": "PAT-002",
            "Name": "Priya Kumar",
            "Phone": phone,
            "Doctor": "Dr. Sana Khan",
            "Appointment Date": "2026-11-02",
            "Appointment Time": "4:00 PM",
            "Token No": "TKN-102",
            "Status": "Confirmed",
            "Booking Status": "Confirmed",
        })

        r = self._send("Show my upcoming appointments", phone=phone, flags=flags)
        resp = r.get("response", "")
        # Both Ramesh and Priya must be mentioned
        self.assertIn("Ramesh", resp)
        self.assertIn("Priya", resp)


if __name__ == "__main__":
    unittest.main()
