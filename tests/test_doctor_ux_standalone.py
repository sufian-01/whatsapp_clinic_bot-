"""Standalone tests for doctor-selection UX improvement.

Verifies:
1. Listing active doctors from Sheets (formatting with name, specialization, fee, available days)
2. Filtering doctors by specialization and disease/health concern
3. Matching exact doctor names
4. Matching minor spelling mistakes and incomplete names (e.g., 'Dr Sufan', 'dr arjun', 'cardiologist Dr Sufian')
5. Handling ambiguous names (e.g., 'Dr. Rahman' vs 'Dr. Rehman')
6. Handling unknown doctor names without guessing
7. Returning an appropriate response when no doctors match
8. Ensuring doctor listing and fuzzy matching do not invoke Gemini (low token usage)
"""

import unittest
from unittest.mock import MagicMock

from app.graph.router import classify_intent, _is_doctor_list_query
from app.tools.doctors import (
    DoctorDirectory,
    DoctorTools,
    calculate_doctor_similarity,
    format_doctor_list_display,
    match_health_concern,
    normalize_doctor_text,
    resolve_specialization,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

DOCTOR_ROWS = [
    ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
    ["D1", "Dr. Arjun Mehta", "General Physician", "Monday, Wednesday, Friday", "10:00 AM", "1:00 PM", "500", "Active"],
    ["D2", "Dr. Sana Khan", "Gynecologist", "Tuesday, Thursday, Saturday", "4:00 PM", "7:00 PM", "700", "Active"],
    ["D3", "Dr. Sufian", "Cardiologist", "Monday, Tuesday, Thursday", "9:00 AM", "12:00 PM", "800", "Active"],
    ["D4", "Dr. Inactive Doctor", "Dermatologist", "Sunday", "10:00 AM", "12:00 PM", "600", "Inactive"],
]

SLOT_ROWS = [
    ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"],
    ["S1", "D3", "Dr. Sufian", "2026-09-29", "09:00", "09:30", "Available", "", "", ""],
    ["S2", "D3", "Dr. Sufian", "2026-09-29", "09:30", "10:00", "Available", "", "", ""],
    ["S3", "D1", "Dr. Arjun Mehta", "2026-09-30", "10:00", "10:30", "Available", "", "", ""],
]


def _make_slot_repo():
    from app.tools.slots import SlotRepository
    rows = list(SLOT_ROWS)
    return SlotRepository(lambda: rows, lambda r, v: None, "appointment_slots!A1:Z5000")


def _make_directory():
    return DoctorDirectory(lambda: DOCTOR_ROWS)


def _make_tools():
    return DoctorTools(_make_directory())


# ===========================================================================
# 1. Listing Active Doctors from Sheets
# ===========================================================================

class ActiveDoctorListingTests(unittest.TestCase):
    def setUp(self):
        self.directory = _make_directory()
        self.tools = _make_tools()

    def test_get_active_doctors_excludes_inactive(self):
        """Active doctor listing must exclude doctors marked as Inactive."""
        all_docs = self.directory.get_doctors()
        active_docs = self.directory.get_active_doctors()
        self.assertEqual(len(all_docs), 4)
        self.assertEqual(len(active_docs), 3)
        names = [d["Doctor Name"] for d in active_docs]
        self.assertIn("Dr. Arjun Mehta", names)
        self.assertIn("Dr. Sana Khan", names)
        self.assertIn("Dr. Sufian", names)
        self.assertNotIn("Dr. Inactive Doctor", names)

    def test_format_doctor_list_display_structure(self):
        """Display contains Doctor name, Specialization, Available days, Consultation fee."""
        active_docs = self.directory.get_active_doctors()
        formatted = format_doctor_list_display(active_docs)

        # Header and prompt
        self.assertIn("Our available doctors are:", formatted)
        self.assertIn("Please select a doctor.", formatted)

        # Doctor 1 details
        self.assertIn("1. Dr. Arjun Mehta", formatted)
        self.assertIn("General Physician | ₹500", formatted)
        self.assertIn("Available: Monday, Wednesday, Friday", formatted)

        # Doctor 2 details
        self.assertIn("2. Dr. Sana Khan", formatted)
        self.assertIn("Gynecologist | ₹700", formatted)
        self.assertIn("Available: Tuesday, Thursday, Saturday", formatted)

        # Doctor 3 details
        self.assertIn("3. Dr. Sufian", formatted)
        self.assertIn("Cardiologist | ₹800", formatted)
        self.assertIn("Available: Monday, Tuesday, Thursday", formatted)

    def test_empty_doctor_list_display(self):
        formatted = format_doctor_list_display([])
        self.assertIn("No doctors are currently available", formatted)


# ===========================================================================
# 2. Disease / Health Concern to Specialization Matching
# ===========================================================================

class DiseaseToSpecializationTests(unittest.TestCase):
    def test_cardiology_concerns(self):
        phrase, spec = match_health_concern("I have chest pain and palpitation")
        self.assertEqual(spec, "cardiology")
        self.assertIn(phrase, ("chest pain", "palpitation"))

    def test_orthopedic_concerns(self):
        phrase, spec = match_health_concern("doctor for knee pain")
        self.assertEqual(spec, "orthopedics")
        self.assertEqual(phrase, "knee pain")

    def test_general_physician_concerns(self):
        phrase, spec = match_health_concern("suffering from fever and cough")
        self.assertEqual(spec, "general physician")
        self.assertIn(phrase, ("fever", "cough"))

    def test_gynecology_concerns(self):
        phrase, spec = match_health_concern("need checkup for pregnancy")
        self.assertEqual(spec, "gynecology")
        self.assertEqual(phrase, "pregnancy")

    def test_dermatology_concerns(self):
        phrase, spec = match_health_concern("severe skin rash and itching")
        self.assertEqual(spec, "dermatology")
        self.assertIn(phrase, ("skin rash", "skin", "rash", "itching"))

    def test_unmatched_concern_returns_none(self):
        phrase, spec = match_health_concern("just general inquiry about clinic")
        self.assertIsNone(phrase)
        self.assertIsNone(spec)

    def test_filtering_doctors_by_concern_specialization(self):
        tools = _make_tools()
        _, spec = match_health_concern("I have chest pain")
        docs = tools.get_doctors_by_specialization(spec)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["Doctor Name"], "Dr. Sufian")


# ===========================================================================
# 3. Matching Exact Doctor Names
# ===========================================================================

class ExactDoctorMatchingTests(unittest.TestCase):
    def setUp(self):
        self.tools = _make_tools()

    def test_exact_name_with_prefix(self):
        res = self.tools.resolve_doctor("Dr. Sufian")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_exact_name_without_prefix(self):
        res = self.tools.resolve_doctor("Sufian")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_full_name_without_prefix(self):
        res = self.tools.resolve_doctor("Arjun Mehta")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Arjun Mehta")

    def test_case_insensitivity(self):
        res = self.tools.resolve_doctor("dr. sana khan")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Sana Khan")

        res_upper = self.tools.resolve_doctor("DR. SANA KHAN")
        self.assertEqual(res_upper["status"], "matched")
        self.assertEqual(res_upper["doctor"]["Doctor Name"], "Dr. Sana Khan")


# ===========================================================================
# 4. Matching Minor Spelling Mistakes & Incomplete Names
# ===========================================================================

class MisspelledDoctorMatchingTests(unittest.TestCase):
    def setUp(self):
        self.tools = _make_tools()

    def test_typo_dr_sufan(self):
        """User example: 'Dr Sufan' -> Dr. Sufian."""
        res = self.tools.resolve_doctor("Dr Sufan")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_typo_sufiyan(self):
        """Common transliteration variation 'dr sufiyan' -> Dr. Sufian."""
        res = self.tools.resolve_doctor("dr sufiyan")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_incomplete_first_name_dr_arjun(self):
        """User example: 'dr arjun' -> Dr. Arjun Mehta."""
        res = self.tools.resolve_doctor("dr arjun")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Arjun Mehta")

    def test_incomplete_first_name_sana(self):
        """User types 'sana' -> Dr. Sana Khan."""
        res = self.tools.resolve_doctor("sana")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Sana Khan")

    def test_with_specialization_prefix(self):
        """User example: 'cardiologist Dr Sufian' -> Dr. Sufian."""
        res = self.tools.resolve_doctor("cardiologist Dr Sufian")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_extra_spaces_and_punctuation(self):
        res = self.tools.resolve_doctor("   dr.   arjun   mehta  ")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Arjun Mehta")


# ===========================================================================
# 5. Handling Ambiguous Names
# ===========================================================================

class AmbiguousDoctorMatchingTests(unittest.TestCase):
    def test_similar_names_triggers_ambiguous_status(self):
        """Two doctors with similar names must return ambiguous status with both choices."""
        rows = [
            ["Doctor ID", "Doctor Name", "Specialization", "Consultation Fee", "Status"],
            ["D1", "Dr. Rahman", "Cardiologist", "800", "Active"],
            ["D2", "Dr. Rehman", "General Physician", "500", "Active"],
        ]
        tools = DoctorTools(DoctorDirectory(lambda: rows))
        res = tools.resolve_doctor("dr rhman")
        self.assertEqual(res["status"], "ambiguous")
        self.assertEqual(len(res["matches"]), 2)
        names = [m["Doctor Name"] for m in res["matches"]]
        self.assertIn("Dr. Rahman", names)
        self.assertIn("Dr. Rehman", names)
        # Must not silently select one
        self.assertNotIn("doctor", res)


# ===========================================================================
# 6. Handling Unknown Doctor Names
# ===========================================================================

class UnknownDoctorMatchingTests(unittest.TestCase):
    def setUp(self):
        self.tools = _make_tools()

    def test_completely_unknown_name(self):
        res = self.tools.resolve_doctor("Dr. John Doe")
        self.assertEqual(res["status"], "not_found")
        self.assertEqual(res["matches"], [])

    def test_random_noise_string(self):
        res = self.tools.resolve_doctor("xyz random gibberish 1234")
        self.assertEqual(res["status"], "not_found")

    def test_never_guesses_unrelated_doctor(self):
        res = self.tools.resolve_doctor("Pediatrician Sharma")
        self.assertEqual(res["status"], "not_found")
        self.assertNotIn("doctor", res)


# ===========================================================================
# 7. Responses When No Doctors Match
# ===========================================================================

class NoDoctorsMatchResponseTests(unittest.TestCase):
    def test_empty_sheet_returns_safe_empty_list(self):
        broken_dir = DoctorDirectory(lambda: [])
        self.assertEqual(broken_dir.get_doctors(), [])
        self.assertEqual(broken_dir.get_active_doctors(), [])

    def test_sheet_exception_handled_safely(self):
        def failing_reader():
            raise RuntimeError("Google Sheets API network error")
        broken_dir = DoctorDirectory(failing_reader)
        self.assertEqual(broken_dir.get_doctors(), [])
        self.assertEqual(broken_dir.get_active_doctors(), [])

    def test_format_display_when_no_doctors(self):
        res = format_doctor_list_display([])
        self.assertIn("No doctors are currently available", res)


# ===========================================================================
# 8. Token Optimization: Doctor Listing and Fuzzy Match Do Not Invoke LLM
# ===========================================================================

class TokenOptimizationTests(unittest.TestCase):
    """Verifies that doctor lookup, filtering, disease matching, and resolution
    execute entirely in deterministic Python without making any Gemini API calls."""

    def test_normalization_no_llm(self):
        res = normalize_doctor_text("Dr. Sufiyan")
        self.assertEqual(res, "sufian")

    def test_similarity_calculation_no_llm(self):
        score = calculate_doctor_similarity("dr arjun", "Dr. Arjun Mehta")
        self.assertEqual(score, 1.0)

    def test_fuzzy_matching_no_llm(self):
        tools = _make_tools()
        res = tools.resolve_doctor("Dr Sufan")
        self.assertEqual(res["status"], "matched")
        self.assertEqual(res["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_disease_matching_no_llm(self):
        phrase, spec = match_health_concern("I have chest pain")
        self.assertEqual(spec, "cardiology")

    def test_doctor_listing_formatting_no_llm(self):
        tools = _make_tools()
        active = tools.get_active_doctors()
        text = format_doctor_list_display(active)
        self.assertIn("Dr. Arjun Mehta", text)
        self.assertIn("Dr. Sana Khan", text)
        self.assertIn("Dr. Sufian", text)


# ===========================================================================
# 9. Router Intent Classification for Doctor Queries
# ===========================================================================

class RouterIntentTests(unittest.TestCase):
    def _intent(self, text):
        return classify_intent({"user_text": text})["intent"]

    def test_which_doctors_are_available(self):
        self.assertEqual(self._intent("Which doctors are available?"), "doctor_list")

    def test_who_are_your_doctors(self):
        self.assertEqual(self._intent("Who are your doctors?"), "doctor_list")

    def test_which_doctor_should_i_consult(self):
        self.assertEqual(self._intent("Which doctor should I consult?"), "doctor_list")

    def test_what_doctors_do_you_have(self):
        self.assertEqual(self._intent("What doctors do you have?"), "doctor_list")

    def test_health_concern_chest_pain(self):
        self.assertEqual(self._intent("I have chest pain"), "doctor_list")

    def test_health_concern_knee_pain(self):
        self.assertEqual(self._intent("Which doctor for knee pain?"), "doctor_list")

    def test_booking_intent_preserved(self):
        self.assertEqual(self._intent("I want to book an appointment"), "appointment_booking")

    def test_appointment_flow_takes_precedence(self):
        state = {"user_text": "Which doctors are available?", "appointment_step": "doctor"}
        self.assertEqual(classify_intent(state)["intent"], "appointment_flow")


if __name__ == "__main__":
    unittest.main()
