"""Unit and integration tests for LangGraph MemorySaver checkpointer,
short-term memory cache, and intelligent multi-turn appointment recall.
"""

from datetime import date
import unittest

from app.channels.whatsapp.handler import WhatsAppHandler
from app.channels.whatsapp.models import (
    WhatsAppMessage,
    WhatsAppMetadata,
    WhatsAppText,
    WhatsAppValue,
)
from app.core.config import Settings
from app.core.sessions import SessionStore
from app.graph.graph import CheckpointedGraph, build_graph
from app.graph.nodes import GraphNodes
from app.graph.router import classify_intent
from app.services.crm_service import CrmService
from app.tools.doctors import DoctorDirectory


class FakePatientRepo:
    def __init__(self, records=None):
        self.records = records or []

    def list_patients(self):
        return [dict(r) for r in self.records]

    def create_patient(self, record):
        rec_dict = {
            "Patient ID": getattr(record, "patient_id", "PAT-1"),
            "Name": getattr(record, "name", ""),
            "Phone": getattr(record, "phone", ""),
            "Email": getattr(record, "email", ""),
            "Doctor": getattr(record, "doctor", ""),
            "Appointment Date": getattr(record, "appointment_date", ""),
            "Appointment Time": getattr(record, "appointment_time", ""),
            "Token No": getattr(record, "token_no", "TKN-1"),
            "Amount": getattr(record, "amount", "800"),
            "Payment Method": getattr(record, "payment_method", "Offline"),
            "Payment Status": getattr(record, "payment_status", "Pending"),
            "Booking Status": getattr(record, "booking_status", "Confirmed"),
            "Status": getattr(record, "status", "Confirmed"),
        }
        self.records.append(rec_dict)
        return {"success": True, "patient": rec_dict}

    def generate_token(self):
        return {"token_no": "TKN-1001"}

    def generate_patient_id(self):
        return {"patient_id": "PAT-1001"}


class FakeLlm:
    def answer(self, system_prompt: str, user_text: str, context: list):
        return f"AI response for: {user_text}"


class FakeRag:
    def search(self, question: str):
        return ["Clinic open Monday-Saturday 9am to 8pm"]


class FakeSlots:
    def __init__(self):
        self.booked = []

    def get_upcoming_available_slots(self, doctor_name: str, doctor_id: str, today_str: str):
        return [
            {
                "Slot ID": "SLOT-SUFIAN-1",
                "Doctor ID": doctor_id,
                "Doctor Name": doctor_name,
                "Date": "2026-10-25",
                "Start Time": "10:00 AM",
                "End Time": "10:30 AM",
                "Status": "Available",
            }
        ]

    def get_available_slots(self, doctor: str, date_str: str):
        return [{"Slot ID": "SLOT-SUFIAN-1", "Start Time": "10:00 AM", "End Time": "10:30 AM"}]

    def book_slot(self, slot_id: str, patient_id: str, token_no: str):
        self.booked.append(slot_id)
        return True

    def release_slot(self, slot_id: str, patient_id: str):
        return True


class FakePayments:
    def record_offline_payment(self, amount: str):
        return {"success": True, "payment_method": "Offline", "payment_status": "Pending", "amount": amount}

    def generate_offline_upi_qr(self, *args, **kwargs):
        return {"success": True, "qr_path": "", "upi_id": "clinic@upi"}


class FakeInvoices:
    def generate_invoice(self, invoice_data, *args, **kwargs):
        return {"success": True, "invoice_number": "INV-2026-001", "file_path": "data/invoices/test.pdf"}


class TestCheckpointerAndMemory(unittest.TestCase):
    def setUp(self):
        self.doctor_rows = [
            ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
            ["DOC-1", "Dr. Sufian", "Cardiologist", "Mon, Tue, Wed, Thu, Fri, Sat", "09:00 AM", "01:00 PM", "800", "Active"],
            ["DOC-2", "Dr. Priya Sharma", "Gynecologist", "Mon, Wed, Fri", "02:00 PM", "06:00 PM", "700", "Active"],
        ]
        self.doctors = DoctorDirectory(lambda: self.doctor_rows)
        self.slots = FakeSlots()
        self.llm = FakeLlm()
        self.rag = FakeRag()
        self.patients = FakePatientRepo()
        self.payments = FakePayments()
        self.invoices = FakeInvoices()
        self.crm = CrmService(patients_tools=self.patients, slots_tools=self.slots)

        self.nodes = GraphNodes(
            clinic_name="City Heart Center",
            llm=self.llm,
            rag=self.rag,
            doctors=self.doctors,
            support_phone="9876543210",
            patients=self.patients,
            slots=self.slots,
            payments=self.payments,
            invoices=self.invoices,
            today_provider=lambda: date(2026, 10, 20),
            crm_service=self.crm,
        )
        self.graph = build_graph(self.nodes)

    def test_01_graph_is_checkpointed_wrapper(self):
        """Verify build_graph returns a CheckpointedGraph instance."""
        self.assertIsInstance(self.graph, CheckpointedGraph)

    def test_02_booking_and_immediate_timing_query(self):
        """Simulate real multi-turn conversation:
        Turn 1: Book Dr Sufian -> Confirm booking (Token generated, last_booked stored).
        Turn 2: Patient asks 'kitne bje aana hai mujhe ?'
        Bot recalls appointment time without re-triggering booking flow.
        """
        thread_id = "wa:tenant_1:919876543210"

        # Turn 1: Direct booking confirmation
        state_t1 = self.graph.invoke({
            "chat_id": thread_id,
            "user_text": "mujhe dr sufian se appointment chahiye",
            "doctor_name": "Dr. Sufian",
            "doctor_id": "DOC-1",
            "appointment_date": "2026-10-25",
            "appointment_time": "10:00 AM",
            "slot_id": "SLOT-SUFIAN-1",
            "amount": "800",
            "patient_name": "Rohit Verma",
            "patient_phone": "9876543210",
            "patient_email": "rohit@example.com",
            "patient_id": "PAT-1001",
            "token_no": "TKN-1001",
            "appointment_step": "confirmation",
        })
        # Finalize offline booking
        res_t1 = self.nodes._complete_offline(state_t1)
        self.assertIn("Appointment confirmed", res_t1["response"])
        self.assertEqual(res_t1.get("last_booked_appointment", {}).get("token_no"), "TKN-1001")
        self.assertEqual(res_t1.get("last_booked_appointment", {}).get("appointment_time"), "10:00 AM")

        # Turn 2: Follow-up question asking reporting time
        res_t2 = self.graph.invoke({
            "chat_id": thread_id,
            "user_text": "kitne bje aana hai mujhe ?",
            "last_booked_appointment": res_t1["last_booked_appointment"],
        })

        self.assertEqual(res_t2["intent"], "patient_appointments")
        self.assertIn("Dr. Sufian", res_t2["response"])
        self.assertIn("10:00 AM", res_t2["response"])
        self.assertIn("TKN-1001", res_t2["response"])
        self.assertIn("10-15 minute pehle", res_t2["response"])

        # Turn 3: Follow-up statement 'maine appoinment book kia hai dr sufian se'
        res_t3 = self.graph.invoke({
            "chat_id": thread_id,
            "user_text": "maine appoinment book kia hai dr sufian se",
            "last_booked_appointment": res_t1["last_booked_appointment"],
        })
        self.assertEqual(res_t3["intent"], "patient_appointments")
        self.assertIn("pehle se confirmed hai", res_t3["response"])
        self.assertIn("TKN-1001", res_t3["response"])

    def test_03_router_recognizes_arrival_and_past_tense_booking(self):
        """Intent classifier identifies timing queries and existing bookings correctly."""
        timing_queries = [
            "kitne bje aana hai mujhe ?",
            "kab aana hai mujhe",
            "mera time kya hai",
            "what time should I come",
            "mujhe kab pahunchna hai",
        ]
        for q in timing_queries:
            intent = classify_intent({"user_text": q})["intent"]
            self.assertEqual(intent, "patient_appointments", f"Failed for query: {q}")

        past_booking_queries = [
            "maine appoinment book kia hai dr sufian se",
            "mai book kr chuka hu",
            "already booked",
            "booking ho chuki hai",
        ]
        for q in past_booking_queries:
            intent = classify_intent({"user_text": q})["intent"]
            self.assertEqual(intent, "patient_appointments", f"Failed for query: {q}")

    def test_04_mid_booking_interruption_does_not_trap_as_name(self):
        """When user says 'arey mei appoinment book kr chuka hu' at name step,
        it does NOT set that sentence as patient name.
        """
        # User in name step
        state = {
            "appointment_step": "name",
            "user_text": "arey mei appoinment book kr chuka hu",
            "doctor_name": "Dr. Sufian",
        }
        res = self.nodes.appointment_progress(state)
        # Should NOT ask for email with user text as name!
        self.assertNotEqual(res.get("patient_name"), "arey mei appoinment book kr chuka hu")
        self.assertNotEqual(res.get("appointment_step"), "email")

    def test_05_email_step_allows_skipping_and_cancelling(self):
        """When user says 'skip' or 'cancel' at email step, it behaves gracefully."""
        # 1. Skip
        res_skip = self.nodes.appointment_progress({
            "appointment_step": "email",
            "user_text": "nahi hai email skip karo",
        })
        self.assertEqual(res_skip["appointment_step"], "phone")
        self.assertIn("phone number", res_skip["response"].lower())

        # 2. Cancel
        res_cancel = self.nodes.appointment_progress({
            "appointment_step": "email",
            "user_text": "cancel",
        })
        self.assertEqual(res_cancel["appointment_step"], "")
        self.assertIn("cancelled", res_cancel["response"].lower())

    def test_06_lookup_by_patient_name_or_token_in_crm(self):
        """When appointment is not in memory, user provides Name or Token, CRM finds it."""
        # Pre-seed patient in CRM
        class Record:
            pass
        rec = Record()
        rec.name = "Rahul Sharma"
        rec.phone = "9988776655"
        rec.email = "rahul@test.com"
        rec.doctor = "Dr. Sufian"
        rec.appointment_date = "2026-10-25"
        rec.appointment_time = "11:00 AM"
        rec.token_no = "TKN-8888"
        rec.amount = "800"
        rec.payment_method = "Offline"
        rec.payment_status = "Pending"
        rec.booking_status = "Confirmed"
        rec.status = "Confirmed"
        rec.patient_id = "PAT-8888"

        self.patients.create_patient(rec)

        # Query by name
        res_name = self.nodes.my_appointments_node({
            "user_text": "Rahul Sharma",
            "reschedule_step": "ask_identifier",
        })
        self.assertIn("TKN-8888", res_name["response"])
        self.assertIn("Dr. Sufian", res_name["response"])
        self.assertIn("11:00 AM", res_name["response"])

        # Query by token
        res_tok = self.nodes.my_appointments_node({
            "user_text": "TKN-8888",
        })
        self.assertIn("TKN-8888", res_tok["response"])
        self.assertIn("Dr. Sufian", res_tok["response"])


if __name__ == "__main__":
    unittest.main()

