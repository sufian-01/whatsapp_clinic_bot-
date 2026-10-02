import unittest

from app.graph.graph import build_graph
from app.graph.nodes import GraphNodes
from app.tools.doctors import DoctorDirectory


ROWS = [
    ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Status"],
    ["D1", "Dr. Sana Khan", "Gynecologist", "Tue, Thu, Sat", "4:00 PM", "7:00 PM", "Active"],
    ["D2", "Dr. Arjun Mehta", "General Physician", "Mon, Wed, Fri", "10:00 AM", "1:00 PM", "Active"],
]


class FakeLlm:
    def answer(self, system_prompt, user_text, context):
        return "context=" + " | ".join(context)


class EmptyRag:
    def search(self, question):
        return []


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.directory = DoctorDirectory(lambda: ROWS)

    def test_get_doctors(self):
        self.assertEqual(len(self.directory.get_doctors()), 2)

    def test_lookup_by_name(self):
        result = self.directory.get_doctor_by_name("dr. sana khan")
        self.assertEqual(result[0]["Specialization"], "Gynecologist")

    def test_lookup_by_specialization(self):
        result = self.directory.get_doctors_by_specialization("gynecologist")
        self.assertEqual(result[0]["Doctor Name"], "Dr. Sana Khan")

    def test_graph_uses_structured_doctor_data(self):
        graph = build_graph(GraphNodes("Test Clinic", FakeLlm(), EmptyRag(), self.directory))
        result = graph.invoke({"user_text": "Which doctors are available?"})
        self.assertIn(result["intent"], ("doctor_information", "doctor_list"))
        self.assertIn("Dr. Sana Khan", result["response"])

    def test_missing_sheet_data_is_safe(self):
        directory = DoctorDirectory(lambda: (_ for _ in ()).throw(RuntimeError("sheet unavailable")))
        self.assertEqual(directory.get_doctors(), [])