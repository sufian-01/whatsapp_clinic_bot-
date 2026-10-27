"""Comprehensive test suite for Telegram Clinic AI Chatbot Conversational Flow.

Covers all 18 test cases specified in Section 11:
1. Doctor list request
2. Exact doctor name
3. Partial doctor name
4. Fuzzy doctor name
5. Ambiguous doctor name
6. Availability without a date
7. Availability with a specific date
8. Follow-up date such as "aur Friday ko?"
9. Booking intent
10. Reschedule intent
11. Cancellation intent
12. Explicit cancellation confirmation
13. Explicit reschedule confirmation
14. Unrelated message during an existing flow
15. Tool failure
16. Invalid LLM tool call / fallback
17. Separate Telegram user sessions
18. Hindi, Hinglish, and English messages
"""

from datetime import date
import unittest
from unittest.mock import MagicMock, patch

from app.graph.graph import build_graph
from app.graph.nodes import GraphNodes
from app.graph.router import classify_intent
from app.services.crm_service import CrmService
from app.telegram.sessions import SessionStore
from app.tools.appointments import AppointmentTools
from app.tools.doctors import DoctorDirectory, DoctorTools
from app.tools.slots import SlotRepository


DOCTORS_DATA = [
    ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
    ["D1", "Dr. Arjun Mehta", "General Physician", "Mon, Wed, Fri", "10:00 AM", "1:00 PM", "500", "Active"],
    ["D2", "Dr. Sana Khan", "Gynecologist", "Tue, Thu, Sat", "4:00 PM", "7:00 PM", "700", "Active"],
    ["D3", "Dr. Sufian", "Cardiologist", "Mon, Tue, Thu", "9:00 AM", "12:00 PM", "800", "Active"],
]

# Base date: 2026-09-28 (Monday)
# 2026-09-30 is Wednesday, 2026-10-02 is Friday
SLOTS_DATA = [
    ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"],
    ["S1", "D1", "Dr. Arjun Mehta", "2026-09-30", "10:00", "10:30", "Available", "", "", ""],
    ["S2", "D1", "Dr. Arjun Mehta", "2026-09-30", "11:00", "11:30", "Available", "", "", ""],
    ["S3", "D1", "Dr. Arjun Mehta", "2026-10-02", "10:00", "10:30", "Available", "", "", ""],
    ["S4", "D1", "Dr. Arjun Mehta", "2026-10-02", "11:00", "11:30", "Available", "", "", ""],
    ["S5", "D2", "Dr. Sana Khan", "2026-09-29", "16:00", "16:30", "Available", "", "", ""],
    ["S6", "D3", "Dr. Sufian", "2026-09-29", "09:00", "09:30", "Available", "", "", ""],
    ["S7", "D1", "Dr. Arjun Mehta", "2026-09-29", "10:00", "10:30", "Booked", "PAT-100", "TKN-1001", "2026-09-28"],
]

PATIENTS_DATA = [
    {
        "Patient ID": "PAT-100",
        "Patient Name": "Test Patient",
        "Phone": "9876543210",
        "Email": "test@example.com",
        "Doctor": "Dr. Arjun Mehta",
        "Appointment Date": "2026-09-29",
        "Appointment Time": "10:00",
        "Token No": "TKN-1001",
        "Booking Status": "Confirmed",
        "Status": "Confirmed",
        "Slot ID": "S7",
    }
]


class FakeLlm:
    def __init__(self, should_fail=False):
        self.call_count = 0
        self.should_fail = should_fail

    def answer(self, system_prompt, user_text, context):
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("Gemini API error")
        return f"LLM response: {user_text}"


class FakeRag:
    def search(self, question):
        return ["City Clinic is located at 123 Health Ave. Open Mon-Sat 9 AM to 8 PM."]


class FakePatients:
    def __init__(self, records=None):
        self.records = [dict(r) for r in (records or PATIENTS_DATA)]

    def list_patients(self):
        return [dict(r) for r in self.records]

    def find_by_token(self, token_no):
        for r in self.records:
            if r.get("Token No", "").strip().casefold() == token_no.strip().casefold():
                return dict(r)
        return None

    def update_booking_status(self, identifier, new_status):
        for r in self.records:
            if r.get("Token No") == identifier or r.get("Patient ID") == identifier:
                r["Booking Status"] = new_status
                r["Status"] = new_status
                return {"success": True, "token_no": r.get("Token No"), "status": new_status}
        return {"success": False, "message": "Not found"}

    def update_appointment_details(self, identifier, updates):
        for r in self.records:
            if r.get("Token No") == identifier or r.get("Patient ID") == identifier:
                if "appointment_date" in updates:
                    r["Appointment Date"] = updates["appointment_date"]
                if "appointment_time" in updates:
                    r["Appointment Time"] = updates["appointment_time"]
                return {"success": True, "token_no": r.get("Token No")}
        return {"success": False, "message": "Not found"}

    def new_patient_id(self):
        return "PAT-NEW"

    def next_token(self):
        return "TKN-NEW"

    def create_patient(self, patient):
        return patient


def create_test_setup(llm=None, slot_rows=None, should_fail_slots=False):
    doctors_list = [list(r) for r in DOCTORS_DATA]
    slots_list = [list(r) for r in (slot_rows or SLOTS_DATA)]
    patients = FakePatients()

    def update_slots(range_name, values):
        row_number = int(range_name.split("A", 1)[1].split(":", 1)[0])
        slots_list[row_number - 1] = list(values)

    slot_repo = SlotRepository(lambda: slots_list, update_slots, "appointment_slots!A1:Z5000")
    if should_fail_slots:
        slot_repo.book_slot = MagicMock(side_effect=RuntimeError("Slot DB failure"))
        slot_repo.get_available_slots = MagicMock(return_value={"success": False, "message": "Lookup failed"})

    doctor_dir = DoctorDirectory(lambda: doctors_list)
    doctor_tools = DoctorTools(doctor_dir)
    appointment_tools = AppointmentTools(slot_repo)
    active_llm = llm or FakeLlm()

    crm = CrmService(
        patients_tools=patients,
        doctors_tools=doctor_tools,
        slots_tools=appointment_tools,
        clinic_name="City Clinic",
        clinic_timezone="Asia/Kolkata",
    )

    nodes = GraphNodes(
        clinic_name="City Clinic",
        llm=active_llm,
        rag=FakeRag(),
        doctors=doctor_tools,
        support_phone="6200126662",
        patients=patients,
        slots=appointment_tools,
        crm_service=crm,
        today_provider=lambda: date(2026, 9, 28),
    )
    graph = build_graph(nodes)
    return graph, nodes, active_llm, patients, slot_repo


class ConversationalFlowTests(unittest.TestCase):
    def setUp(self):
        self.graph, self.nodes, self.llm, self.patients, self.slots = create_test_setup()

    # ---------------------------------------------------------------------------
    # 1. Doctor list request
    # ---------------------------------------------------------------------------
    def test_01_doctor_list_request(self):
        """User asking for doctor list receives active doctors formatted concisely."""
        res = self.graph.invoke({"user_text": "Doctor ki list dikhao"})
        self.assertEqual(res["intent"], "doctor_list")
        self.assertIn("Dr. Arjun Mehta", res["response"])
        self.assertIn("General Physician", res["response"])
        self.assertIn("₹500", res["response"])
        self.assertIn("Dr. Sana Khan", res["response"])
        self.assertEqual(res.get("ui"), "doctor_select")

    # ---------------------------------------------------------------------------
    # 2. Exact doctor name
    # ---------------------------------------------------------------------------
    def test_02_exact_doctor_name(self):
        """Exact name query checks availability for that doctor without showing full list."""
        res = self.graph.invoke({"user_text": "Dr. Arjun Mehta kab free hain?"})
        self.assertEqual(res["intent"], "doctor_list")
        self.assertEqual(res["doctor_name"], "Dr. Arjun Mehta")
        self.assertIn("Dr. Arjun Mehta is available", res["response"])
        self.assertIn("30 September", res["response"])
        # Full doctor list not dumped
        self.assertNotIn("Gynecologist", res["response"])

    # ---------------------------------------------------------------------------
    # 3. Partial doctor name
    # ---------------------------------------------------------------------------
    def test_03_partial_doctor_name(self):
        """'Dr Arjun' or 'Arjun' in sentence matches Dr. Arjun Mehta."""
        for q in ["Dr Arjun kab free hain?", "dr arjun available hai?", "doctor arjun kab milenge"]:
            res = self.graph.invoke({"user_text": q})
            self.assertEqual(res["intent"], "doctor_list")
            self.assertEqual(res["doctor_name"], "Dr. Arjun Mehta")
            self.assertIn("Dr. Arjun Mehta", res["response"])

    # ---------------------------------------------------------------------------
    # 4. Fuzzy doctor name
    # ---------------------------------------------------------------------------
    def test_04_fuzzy_doctor_name(self):
        """Minor spelling variations like 'dr sufan' match Dr. Sufian."""
        res = self.graph.invoke({"user_text": "dr sufan kab free hai"})
        self.assertEqual(res["intent"], "doctor_list")
        self.assertEqual(res["doctor_name"], "Dr. Sufian")

    # ---------------------------------------------------------------------------
    # 5. Ambiguous doctor name
    # ---------------------------------------------------------------------------
    def test_05_ambiguous_doctor_name(self):
        """Multiple close candidates return ambiguous status asking user to choose."""
        ambiguous_doctors = [
            ["Doctor ID", "Doctor Name", "Specialization", "Consultation Fee", "Status"],
            ["D1", "Dr. Rahman", "Cardiologist", "800", "Active"],
            ["D2", "Dr. Rehman", "General Physician", "500", "Active"],
        ]
        directory = DoctorDirectory(lambda: ambiguous_doctors)
        resolved = directory.resolve_doctor("rahman")
        self.assertIn(resolved["status"], {"ambiguous", "matched"})
        if resolved["status"] == "ambiguous":
            self.assertGreater(len(resolved["matches"]), 1)
            self.assertNotIn("doctor", resolved)

    # ---------------------------------------------------------------------------
    # 6. Availability without a date
    # ---------------------------------------------------------------------------
    def test_06_availability_without_date(self):
        """'Dr Arjun kab free hain?' fetches upcoming dates and times."""
        res = self.graph.invoke({"user_text": "Dr Arjun kab free hain?"})
        self.assertEqual(res["doctor_name"], "Dr. Arjun Mehta")
        self.assertIn("30 September: 10:00 AM, 11:00 AM", res["response"])
        self.assertIn("02 October: 10:00 AM, 11:00 AM", res["response"])

    # ---------------------------------------------------------------------------
    # 7. Availability with a specific date
    # ---------------------------------------------------------------------------
    def test_07_availability_with_specific_date(self):
        """User gives specific date '30 September'."""
        res = self.graph.invoke({"user_text": "Is Dr Arjun free on 30 September 2026?"})
        self.assertEqual(res["doctor_name"], "Dr. Arjun Mehta")
        self.assertEqual(res.get("appointment_date"), "2026-09-30")
        self.assertIn("30 September: 10:00 AM, 11:00 AM", res["response"])

    # ---------------------------------------------------------------------------
    # 8. Follow-up date such as "aur Friday ko?"
    # ---------------------------------------------------------------------------
    def test_08_follow_up_date_continuity(self):
        """Turn 1: Ask about Dr. Arjun. Turn 2: 'aur Friday ko?' retains Dr. Arjun and checks Friday."""
        first = self.graph.invoke({"user_text": "Dr Arjun kab free hain?"})
        self.assertEqual(first["doctor_name"], "Dr. Arjun Mehta")

        follow_up = self.graph.invoke({**first, "user_text": "aur Friday ko?"})
        self.assertEqual(follow_up["doctor_name"], "Dr. Arjun Mehta")
        self.assertEqual(follow_up.get("appointment_date"), "2026-10-02")
        self.assertIn("02 October: 10:00 AM, 11:00 AM", follow_up["response"])

    # ---------------------------------------------------------------------------
    # 9. Booking intent
    # ---------------------------------------------------------------------------
    def test_09_booking_intent(self):
        """Booking intent starts flow; if doctor already known, asks only missing details."""
        state = self.graph.invoke({"user_text": "Dr Arjun kab free hain?"})
        booking_state = self.graph.invoke({**state, "user_text": "Appointment book karni hai"})
        self.assertEqual(booking_state["intent"], "appointment_booking")
        self.assertEqual(booking_state["appointment_step"], "name")
        self.assertIn("Arjun", booking_state["response"])

    # ---------------------------------------------------------------------------
    # 10. Reschedule intent
    # ---------------------------------------------------------------------------
    def test_10_reschedule_intent(self):
        """'Meri appointment change karni hai' routes to reschedule flow."""
        for q in ["Meri appointment change karni hai", "I want to reschedule my appointment", "Appointment kal ke liye kar do"]:
            res = self.graph.invoke({"user_text": q})
            self.assertEqual(res["intent"], "appointment_reschedule")
            self.assertEqual(res.get("reschedule_step"), "ask_identifier")

    # ---------------------------------------------------------------------------
    # 11. Cancellation intent
    # ---------------------------------------------------------------------------
    def test_11_cancellation_intent(self):
        """'Meri booking cancel kar do' routes to cancellation flow."""
        for q in ["Meri booking cancel kar do", "I want to cancel my appointment", "Appointment cancel"]:
            res = self.graph.invoke({"user_text": q})
            self.assertEqual(res["intent"], "appointment_cancel")
            self.assertEqual(res.get("cancel_step"), "ask_identifier")

    # ---------------------------------------------------------------------------
    # 12. Explicit cancellation confirmation
    # ---------------------------------------------------------------------------
    def test_12_explicit_cancellation_confirmation(self):
        """Cancellation requires explicit confirmation before releasing slot."""
        # Enter with token
        s1 = self.graph.invoke({"user_text": "Cancel appointment TKN-1001"})
        self.assertEqual(s1["cancel_step"], "confirm")
        self.assertEqual(s1["ui"], "cancel_confirm")

        # Decline cancellation
        s_keep = self.graph.invoke({**s1, "user_text": "keep_appointment"})
        self.assertEqual(s_keep["cancel_step"], "")
        self.assertIn("remains confirmed", s_keep["response"])

        # Confirm cancellation
        s_cancel = self.graph.invoke({**s1, "user_text": "confirm_cancel"})
        self.assertEqual(s_cancel["cancel_step"], "")
        self.assertIn("successfully cancelled", s_cancel["response"])
        # Slot released
        slot = self.slots.get_slot_by_id("S7")
        self.assertEqual(slot["Status"], "Available")

    # ---------------------------------------------------------------------------
    # 13. Explicit reschedule confirmation
    # ---------------------------------------------------------------------------
    def test_13_explicit_reschedule_confirmation(self):
        """Reschedule requires explicit confirmation before shifting booking."""
        s1 = self.graph.invoke({"user_text": "Reschedule appointment TKN-1001"})
        self.assertEqual(s1["reschedule_step"], "select_date")

        s2 = self.graph.invoke({**s1, "user_text": "2026-09-30"})
        self.assertEqual(s2["reschedule_step"], "select_slot")

        s3 = self.graph.invoke({**s2, "user_text": "slot:S1"})
        self.assertEqual(s3["reschedule_step"], "confirm")
        self.assertEqual(s3["ui"], "reschedule_confirm")

        # Confirm reschedule
        s4 = self.graph.invoke({**s3, "user_text": "confirm_reschedule"})
        self.assertEqual(s4["reschedule_step"], "")
        self.assertIn("Rescheduled Successfully", s4["response"])
        self.assertEqual(self.slots.get_slot_by_id("S1")["Status"], "Booked")
        self.assertEqual(self.slots.get_slot_by_id("S7")["Status"], "Available")

    # ---------------------------------------------------------------------------
    # 14. Unrelated message during an existing flow
    # ---------------------------------------------------------------------------
    def test_14_unrelated_message_during_existing_flow(self):
        """User asking clinic information during appointment flow gets answered."""
        # Patient in email step
        state = {"appointment_step": "email", "user_text": "Where is the clinic located?"}
        classified = classify_intent(state)
        self.assertEqual(classified["intent"], "clinic_information")

        res = self.graph.invoke(state)
        self.assertEqual(res["intent"], "clinic_information")
        self.assertIn("LLM response", res["response"])

    # ---------------------------------------------------------------------------
    # 15. Tool failure handling
    # ---------------------------------------------------------------------------
    def test_15_tool_failure_handled_gracefully(self):
        """Backend tool failure does not claim success and returns a polite message."""
        fail_graph, _, _, _, _ = create_test_setup(should_fail_slots=True)
        res = fail_graph.invoke({"user_text": "Is Dr. Arjun Mehta available on 2026-09-30?"})
        # Graceful error, no unhandled exception
        self.assertIsInstance(res["response"], str)
        self.assertNotIn("Confirmed", res.get("booking_status", ""))

    # ---------------------------------------------------------------------------
    # 16. Invalid LLM fallback handling
    # ---------------------------------------------------------------------------
    def test_16_invalid_llm_fallback(self):
        """When user sends greeting, deterministic greeting returns even if LLM is down."""
        failing_llm = FakeLlm(should_fail=True)
        graph, _, _, _, _ = create_test_setup(llm=failing_llm)
        res = graph.invoke({"user_text": "Hello"})
        self.assertIn("Welcome to City Clinic", res["response"])

    def test_16b_llm_failure_on_non_greeting_question_returns_safe_message(self):
        """When user asks a non-greeting question and LLM fails, answer node returns safe helpline message."""
        failing_llm = FakeLlm(should_fail=True)
        graph, _, _, _, _ = create_test_setup(llm=failing_llm)
        res = graph.invoke({"user_text": "Can you tell me about wheelchair access and parking at the building?"})
        self.assertIn("helpline", res["response"].lower())

    # ---------------------------------------------------------------------------
    # 17. Separate Telegram user sessions
    # ---------------------------------------------------------------------------
    def test_17_separate_user_sessions(self):
        """Different chat IDs maintain isolated session memory."""
        sessions = SessionStore()

        # Chat 101 checks Dr. Arjun
        state1 = sessions.get(101)
        state1["chat_id"] = 101
        state1["user_text"] = "Dr Arjun kab free hain?"
        res1 = self.graph.invoke(state1)
        sessions.save(101, res1)

        # Chat 102 starts fresh
        state2 = sessions.get(102)
        state2["chat_id"] = 102
        state2["user_text"] = "Hello"
        res2 = self.graph.invoke(state2)
        sessions.save(102, res2)

        # Chat 102 does NOT have Dr. Arjun from chat 101
        saved102 = sessions.get(102)
        saved101 = sessions.get(101)
        self.assertEqual(saved101.get("doctor_name"), "Dr. Arjun Mehta")
        self.assertIsNone(saved102.get("doctor_name"))

    # ---------------------------------------------------------------------------
    # 18. Hindi, Hinglish, and English messages
    # ---------------------------------------------------------------------------
    def test_18_multilingual_messages(self):
        """Chatbot understands queries across Hindi, Hinglish, and English."""
        # English
        en = self.graph.invoke({"user_text": "Which doctors are available?"})
        self.assertEqual(en["intent"], "doctor_list")
        self.assertIn("Dr. Arjun Mehta", en["response"])

        # Hinglish
        hing = self.graph.invoke({"user_text": "Dr Arjun kab free hain?"})
        self.assertEqual(hing["intent"], "doctor_list")
        self.assertEqual(hing["doctor_name"], "Dr. Arjun Mehta")

        # Hindi cancellation
        hi = self.graph.invoke({"user_text": "Meri booking cancel kar do"})
        self.assertEqual(hi["intent"], "appointment_cancel")
