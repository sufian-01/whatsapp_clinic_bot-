"""Availability conversation tests backed only by mocked Google Sheet rows."""

from datetime import date
import unittest

from app.graph.graph import build_graph
from app.graph.nodes import GraphNodes
from app.tools.appointments import AppointmentTools
from app.tools.doctors import DoctorDirectory, DoctorTools
from app.tools.slots import SlotRepository


DOCTORS = [
    ["Doctor ID", "Doctor Name", "Specialization", "Consultation Fee", "Status"],
    ["D1", "Dr. Arjun Mehta", "General Physician", "500", "Active"],
    ["D2", "Dr. Sana Khan", "Gynecologist", "700", "Active"],
]
SLOTS = [
    ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"],
    ["A1", "D1", "Dr. Arjun Mehta", "2026-09-30", "10:00", "10:30", "Available", "", "", ""],
    ["A2", "D1", "Dr. Arjun Mehta", "2026-09-30", "11:00", "11:30", "Available", "", "", ""],
    ["A3", "D1", "Dr. Arjun Mehta", "2026-10-02", "12:00", "12:30", "Available", "", "", ""],
    ["B1", "D2", "Dr. Sana Khan", "2026-10-01", "09:00", "09:30", "Available", "", "", ""],
    ["B2", "D2", "Dr. Sana Khan", "2026-10-01", "10:00", "10:30", "Booked", "P1", "T1", "now"],
    # Duplicate rows and malformed dates must not become patient-facing slots.
    ["A1", "D1", "Dr. Arjun Mehta", "2026-09-30", "10:00", "10:30", "Available", "", "", ""],
    ["BAD", "D1", "Dr. Arjun Mehta", "not-a-date", "13:00", "13:30", "Available", "", "", ""],
]


class FakeLlm:
    def answer(self, system_prompt, user_text, context):
        return "llm fallback"


class FakeRag:
    def search(self, question):
        return []


def make_graph(rows=None):
    sheet_rows = list(rows or SLOTS)
    repository = SlotRepository(lambda: sheet_rows, lambda range_name, values: None, "appointment_slots!A1:Z5000")
    nodes = GraphNodes(
        "Test Clinic",
        FakeLlm(),
        FakeRag(),
        doctors=DoctorTools(DoctorDirectory(lambda: DOCTORS)),
        slots=AppointmentTools(repository),
        today_provider=lambda: date(2026, 9, 29),
    )
    return build_graph(nodes)


class DoctorAvailabilityTests(unittest.TestCase):
    def test_named_doctor_free_slots_are_grouped_from_sheet(self):
        result = make_graph().invoke({"user_text": "When is Dr. Arjun Mehta free?"})
        self.assertIn("Dr. Arjun Mehta is available", result["response"])
        self.assertIn("30 September: 10:00 AM, 11:00 AM", result["response"])
        self.assertIn("02 October: 12:00 PM", result["response"])

    def test_tomorrow_uses_clinic_today_and_shows_only_unbooked_times(self):
        result = make_graph().invoke({"user_text": "Is Dr. Arjun Mehta available tomorrow?"})
        self.assertIn("30 September", result["response"])
        self.assertIn("10:00 AM", result["response"])
        self.assertIn("11:00 AM", result["response"])

    def test_date_without_slots_offers_nearest_upcoming_dates(self):
        result = make_graph().invoke({"user_text": "Is Dr. Arjun Mehta available on 1 October 2026?"})
        self.assertIn("no available slots", result["response"])
        self.assertIn("02 October", result["response"])

    def test_selected_doctor_is_retained_for_hinglish_follow_up(self):
        graph = make_graph()
        first = graph.invoke({"user_text": "When is Dr. Arjun Mehta free?"})
        follow_up = graph.invoke({**first, "user_text": "aur kab free hain?"})
        self.assertEqual(follow_up["doctor_name"], "Dr. Arjun Mehta")
        self.assertIn("Dr. Arjun Mehta is available", follow_up["response"])

    def test_general_availability_uses_real_slot_data_and_hides_booked_slot(self):
        result = make_graph().invoke({"user_text": "Which doctors are available?"})
        self.assertIn("Dr. Arjun Mehta", result["response"])
        self.assertIn("Dr. Sana Khan", result["response"])
        self.assertIn("9:00 AM", result["response"])
        self.assertNotIn("10:00 AM, more", result["response"])

    def test_empty_sheet_never_fabricates_availability(self):
        headers_only = [SLOTS[0]]
        result = make_graph(headers_only).invoke({"user_text": "When is Dr. Arjun Mehta free?"})
        self.assertIn("no upcoming available slots", result["response"])

    def test_booking_with_named_doctor_shows_availability_before_patient_details(self):
        result = make_graph().invoke({"user_text": "I want to book Dr. Arjun Mehta"})
        self.assertEqual(result["appointment_step"], "pre_patient_date")
        self.assertIn("30 September", result["response"])
        self.assertNotIn("May I know your name", result["response"])

    def test_booking_date_selects_slots_without_reasking_for_date(self):
        graph = make_graph()
        state = graph.invoke({"user_text": "I want to book Dr. Arjun Mehta"})
        state = graph.invoke({**state, "user_text": "30 September"})
        self.assertEqual(state["appointment_step"], "pre_patient_slot")
        self.assertIn("Available slots on 30 September 2026", state["response"])

    def test_changing_doctor_rechecks_new_doctor_availability(self):
        graph = make_graph()
        state = graph.invoke({"user_text": "I want to book Dr. Arjun Mehta"})
        state = graph.invoke({**state, "user_text": "Dr. Sana Khan"})
        self.assertEqual(state["doctor_name"], "Dr. Sana Khan")
        self.assertIn("01 October", state["response"])


if __name__ == "__main__":
    unittest.main()
