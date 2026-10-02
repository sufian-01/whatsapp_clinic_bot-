import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.graph.graph import build_graph
from app.graph.nodes import GraphNodes
from app.tools.doctors import DoctorDirectory
from app.tools.patients import PatientRecord


class FakeLlm:
    def answer(self, system_prompt, user_text, context):
        return "llm"


class FakeRag:
    def search(self, question):
        return []


class FakeSlots:
    def __init__(self):
        self.booked = False

    def get_available_slots(self, doctor, date):
        return [] if self.booked else [{"Slot ID": "S1", "Start Time": "10:00", "End Time": "10:30"}]

    def book_slot(self, slot_id, patient_id, token_no):
        if self.booked:
            return False
        self.booked = True
        return True

    def release_slot_if_needed(self, slot_id, patient_id=None):
        self.booked = False
        return True


class FakePatients:
    def new_patient_id(self):
        return "PAT-NEW"

    def next_token(self):
        return "TKN-0001"

    def create_patient(self, patient):
        return patient


class AppointmentFlowTests(unittest.TestCase):
    def setUp(self):
        rows = [["Doctor ID", "Doctor Name", "Specialization", "Consultation Fee"], ["D1", "Dr. Sana Khan", "Gynecologist", "700"]]
        self.slots = FakeSlots()
        self.patients = FakePatients()
        nodes = GraphNodes("Test Clinic", FakeLlm(), FakeRag(), DoctorDirectory(lambda: rows), "6200126662", self.patients, self.slots)
        self.graph = build_graph(nodes)

    def send(self, state, text):
        state = dict(state)
        state["user_text"] = text
        return self.graph.invoke(state)

    def test_progressive_flow_reaches_payment(self):
        state = self.graph.invoke({"user_text": "I want to book an appointment"})
        state = self.send(state, "Patient Name")
        state = self.send(state, "patient@example.com")
        state = self.send(state, "+911234")
        state = self.send(state, "Dr. Sana Khan")
        state = self.send(state, "tomorrow")
        self.assertEqual(state["ui"], "slots")
        state = self.send(state, "S1")
        self.assertEqual(state["ui"], "confirm")
        state = self.send(state, "confirm")
        self.assertEqual(state["appointment_step"], "payment")
        self.assertEqual(state["ui"], "payment")

    def test_online_payment_is_only_a_placeholder(self):
        state = self.graph.invoke({"user_text": "I want to book an appointment"})
        state["appointment_step"] = "payment"
        state["slot_id"] = "S1"
        state["patient_id"] = "PAT-NEW"
        result = self.send(state, "payment_online")
        self.assertIn("available soon", result["response"])
        self.assertNotEqual(result.get("payment_status"), "Paid")

    def test_offline_payment_generates_pending_confirmation(self):
        state = self.graph.invoke({"user_text": "I want to book an appointment"})
        for text in ["Patient Name", "patient@example.com", "+911234", "Dr. Sana Khan", "tomorrow", "S1", "confirm"]:
            state = self.send(state, text)
        with tempfile.TemporaryDirectory() as directory:
            fake_invoice = Path(directory, "invoice.pdf")
            fake_invoice.write_bytes(b"pdf")
            with patch("app.tools.invoices.generate_invoice", return_value={"success": True, "invoice_number": "INV-1", "file_path": str(fake_invoice)}):
                result = self.send(state, "payment_offline")
        self.assertEqual(result["payment_status"], "Pending")
        self.assertEqual(result["booking_status"], "Confirmed")
        self.assertEqual(result["token_no"], "TKN-0001")
        repeated = self.send(result, "payment_offline")
        self.assertEqual(repeated["token_no"], "TKN-0001")
