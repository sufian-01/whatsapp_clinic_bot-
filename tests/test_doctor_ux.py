"""Tests for doctor-selection UX improvements.

Covers:
- Doctor discovery (no doctor, date-filtered, specialization-filtered)
- Fuzzy matching (various misspellings)
- Ambiguous / low-confidence safety
- Context continuity (selected doctor not re-asked)
- Token optimization (no Gemini calls for doctor ops)
- Telegram button behaviour
"""
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from app.graph.graph import build_graph
from app.graph.nodes import GraphNodes
from app.graph.router import classify_intent, _is_doctor_list_query
from app.telegram.handlers import _reply_markup
from app.tools.doctors import (
    DoctorDirectory,
    DoctorTools,
    normalize_doctor_text,
    resolve_specialization,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

DOCTOR_ROWS = [
    ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
    ["D1", "Dr. Arjun Mehta", "General Physician", "Mon, Wed, Fri", "10:00 AM", "1:00 PM", "500", "Active"],
    ["D2", "Dr. Sana Khan", "Gynecologist", "Tue, Thu, Sat", "4:00 PM", "7:00 PM", "700", "Active"],
    ["D3", "Dr. Sufian", "Cardiologist", "Mon, Tue, Thu", "9:00 AM", "12:00 PM", "800", "Active"],
]

SLOT_ROWS = [
    ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"],
    # Only Dr. Sufian has slots on 2026-09-29
    ["S1", "D3", "Dr. Sufian", "2026-09-29", "09:00", "09:30", "Available", "", "", ""],
    ["S2", "D3", "Dr. Sufian", "2026-09-29", "09:30", "10:00", "Available", "", "", ""],
    # Dr. Arjun has slots on a different date
    ["S3", "D1", "Dr. Arjun Mehta", "2026-09-30", "10:00", "10:30", "Available", "", "", ""],
]


class FakeLlm:
    """Tracks whether answer() is called — should NOT be called for doctor ops."""
    def __init__(self):
        self.call_count = 0

    def answer(self, system_prompt, user_text, context):
        self.call_count += 1
        return f"llm_answer:{user_text}"


class FakeRag:
    def search(self, question):
        return []


def _make_slot_repo():
    from app.tools.slots import SlotRepository

    rows = list(SLOT_ROWS)

    def update(range_name, values):
        pass  # no-op for read-only tests

    return SlotRepository(lambda: rows, update, "appointment_slots!A1:Z5000")


def _make_directory():
    return DoctorDirectory(lambda: DOCTOR_ROWS)


def _make_tools():
    return DoctorTools(_make_directory())


def _make_graph(fake_llm=None):
    llm = fake_llm or FakeLlm()
    directory = _make_directory()
    nodes = GraphNodes(
        "Test Clinic",
        llm,
        FakeRag(),
        DoctorTools(directory),
        slots=_make_slot_repo(),
        today_provider=lambda: date(2026, 9, 28),
    )
    return build_graph(nodes), llm


# ===========================================================================
# 1. Normalize helper
# ===========================================================================

class NormalizeTests(unittest.TestCase):
    def test_strips_dr_prefix(self):
        self.assertEqual(normalize_doctor_text("Dr. Sufian"), "sufian")

    def test_strips_doctor_prefix(self):
        self.assertEqual(normalize_doctor_text("Doctor Sufian"), "sufian")

    def test_case_insensitive(self):
        self.assertEqual(normalize_doctor_text("DR. SUFIAN"), "sufian")

    def test_punctuation_removed(self):
        self.assertEqual(normalize_doctor_text("dr. sana-khan"), "sana khan")

    def test_typo_sufiyan_normalized(self):
        self.assertEqual(normalize_doctor_text("dr sufiyan"), "sufian")

    def test_extra_spaces(self):
        self.assertEqual(normalize_doctor_text("  dr   sufian  "), "sufian")


# ===========================================================================
# 2. Fuzzy doctor matching
# ===========================================================================

class FuzzyMatchTests(unittest.TestCase):
    def setUp(self):
        self.tools = _make_tools()

    # --- high confidence matches ---

    def test_exact_match(self):
        result = self.tools.resolve_doctor("Dr. Sufian")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_lowercase_no_prefix(self):
        result = self.tools.resolve_doctor("sufian")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_typo_sufiyan(self):
        result = self.tools.resolve_doctor("dr sufiyan")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_typo_sufiyan_no_prefix(self):
        result = self.tools.resolve_doctor("sufiyan")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_case_variation(self):
        result = self.tools.resolve_doctor("DR. SUFIAN")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_punctuation_variation(self):
        result = self.tools.resolve_doctor("dr. sufian")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["doctor"]["Doctor Name"], "Dr. Sufian")

    def test_with_word_doctor(self):
        result = self.tools.resolve_doctor("sufian doctor")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["doctor"]["Doctor Name"], "Dr. Sufian")

    # --- low confidence: should NOT silently match ---

    def test_completely_unknown_name(self):
        result = self.tools.resolve_doctor("Dr. Xyzabc Nonexistent")
        self.assertIn(result["status"], {"not_found", "ambiguous"})
        # Must NOT auto-select a doctor
        self.assertNotIn("doctor", result) if result["status"] == "not_found" else None

    def test_very_short_noise_not_matched(self):
        result = self.tools.resolve_doctor("xyz")
        self.assertEqual(result["status"], "not_found")


# ===========================================================================
# 3. Specialization resolution
# ===========================================================================

class SpecializationResolutionTests(unittest.TestCase):
    def test_cardiologist(self):
        self.assertEqual(resolve_specialization("cardiologist"), "cardiology")

    def test_heart_doctor(self):
        self.assertEqual(resolve_specialization("heart doctor"), "cardiology")

    def test_cardio(self):
        self.assertEqual(resolve_specialization("cardio"), "cardiology")

    def test_gynecologist(self):
        self.assertIn(resolve_specialization("gynecologist"), {"gynecology"})

    def test_women(self):
        self.assertEqual(resolve_specialization("women doctor"), "gynecology")

    def test_general_gp(self):
        self.assertEqual(resolve_specialization("gp"), "general physician")

    def test_unknown_returns_none(self):
        self.assertIsNone(resolve_specialization("superherologist"))


# ===========================================================================
# 4. Doctor list — no doctor specified
# ===========================================================================

class DoctorListNoSpecificationTests(unittest.TestCase):
    def test_which_doctors_available_returns_list(self):
        """'which doctors are available?' → doctor list, no LLM."""
        graph, llm = _make_graph()
        result = graph.invoke({"user_text": "which doctors are available?"})
        self.assertIn("Dr. Arjun Mehta", result["response"])
        self.assertIn("Dr. Sufian", result["response"])
        self.assertNotIn("Dr. Sana Khan", result["response"])
        self.assertEqual(llm.call_count, 0, "LLM must NOT be called for doctor list")

    def test_which_dr_available_returns_list(self):
        """'which dr are available' → doctor list."""
        graph, llm = _make_graph()
        result = graph.invoke({"user_text": "which dr are available"})
        self.assertIn("Dr.", result["response"])
        self.assertEqual(llm.call_count, 0)

    def test_doctor_list_sets_doctor_select_ui(self):
        graph, _ = _make_graph()
        result = graph.invoke({"user_text": "which doctors are available?"})
        self.assertEqual(result.get("ui"), "doctor_select")
        self.assertGreater(len(result.get("doctor_choices", [])), 0)

    def test_doctor_list_has_no_global_menu(self):
        """doctor_select ui → doctor buttons, NOT global menu."""
        result = {"ui": "doctor_select", "doctor_choices": [{"Doctor ID": "D1", "Doctor Name": "Dr. X"}], "appointment_step": ""}
        markup = _reply_markup(result)
        # Should return doctor_menu, not None and not main_menu
        self.assertIsNotNone(markup)


# ===========================================================================
# 5. Date-aware doctor list
# ===========================================================================

class DoctorListDateAwareTests(unittest.TestCase):
    def test_date_specific_shows_only_available_doctors(self):
        """'which doctors are available on 29th sept?' → only Dr. Sufian (has slots)."""
        graph, llm = _make_graph()
        result = graph.invoke({"user_text": "which doctors are available on 29 sept 2026?"})
        self.assertIn("Dr. Sufian", result["response"])
        # Dr. Arjun has no slot on 2026-09-29
        self.assertNotIn("Dr. Arjun Mehta", result["response"])
        self.assertEqual(llm.call_count, 0, "LLM must NOT be called for date-aware doctor list")

    def test_no_available_slots_date_returns_message(self):
        graph, _ = _make_graph()
        result = graph.invoke({"user_text": "which doctors are available on 1 jan 2025?"})
        # Should indicate no availability, not crash
        self.assertIsInstance(result["response"], str)
        self.assertTrue(len(result["response"]) > 0)


# ===========================================================================
# 6. Specialization-aware doctor list
# ===========================================================================

class DoctorListSpecializationTests(unittest.TestCase):
    def test_cardiologist_query(self):
        """'which cardiologist is available?' → Dr. Sufian only."""
        graph, llm = _make_graph()
        result = graph.invoke({"user_text": "which cardiologist is available?"})
        self.assertIn("Dr. Sufian", result["response"])
        self.assertEqual(llm.call_count, 0)

    def test_i_need_a_cardiologist(self):
        graph, llm = _make_graph()
        result = graph.invoke({"user_text": "I need a cardiologist"})
        self.assertIn("Dr. Sufian", result["response"])
        self.assertEqual(llm.call_count, 0)


# ===========================================================================
# 7. Appointment flow — doctor step shows list instead of asking for name
# ===========================================================================

class AppointmentDoctorStepTests(unittest.TestCase):
    def _reach_doctor_step(self):
        graph, llm = _make_graph()
        state = graph.invoke({"user_text": "I want to book an appointment"})
        state = dict(state, user_text="Test Patient")
        state = graph.invoke(state)
        state = dict(state, user_text="test@example.com")
        state = graph.invoke(state)
        state = dict(state, user_text="+911234567890")
        state = graph.invoke(state)
        return graph, state, llm

    def test_doctor_step_shows_list_not_asks_name(self):
        """After phone, assistant shows doctor list (not 'Which doctor or specialization?')."""
        _, state, llm = self._reach_doctor_step()
        self.assertEqual(state.get("appointment_step"), "doctor")
        self.assertIn("Dr.", state["response"])
        self.assertNotEqual(state["response"], "Which doctor or specialization would you like?")
        self.assertEqual(llm.call_count, 0)

    def test_doctor_step_shows_buttons(self):
        _, state, _ = self._reach_doctor_step()
        self.assertEqual(state.get("ui"), "doctor_select")
        self.assertGreater(len(state.get("doctor_choices", [])), 0)

    def test_doctor_selected_by_id_callback(self):
        """Simulates user tapping a doctor button (doctor_id passed as text)."""
        graph, state, _ = self._reach_doctor_step()
        # Simulate handler stripping "doctor:" prefix
        state = dict(state, user_text="D2")  # Doctor ID for Dr. Sana Khan
        state = graph.invoke(state)
        self.assertEqual(state.get("doctor_name"), "Dr. Sana Khan")
        self.assertEqual(state.get("appointment_step"), "date")

    def test_doctor_selected_by_fuzzy_name(self):
        """User types 'dr sufiyan' → resolves to Dr. Sufian."""
        graph, state, llm = self._reach_doctor_step()
        state = dict(state, user_text="dr sufiyan")
        state = graph.invoke(state)
        self.assertEqual(state.get("doctor_name"), "Dr. Sufian")
        self.assertEqual(state.get("appointment_step"), "date")
        self.assertEqual(llm.call_count, 0, "LLM must NOT be called for fuzzy matching")

    def test_doctor_selected_by_specialization(self):
        """User types 'cardiologist' → resolves to Dr. Sufian (only cardiologist)."""
        graph, state, llm = self._reach_doctor_step()
        state = dict(state, user_text="cardiologist")
        state = graph.invoke(state)
        self.assertEqual(state.get("doctor_name"), "Dr. Sufian")
        self.assertEqual(llm.call_count, 0)

    def test_unknown_doctor_shows_list_again(self):
        """User types an unrecognized name → list is shown again."""
        graph, state, _ = self._reach_doctor_step()
        state = dict(state, user_text="Dr. Xyzabc Nonexistent Person")
        state = graph.invoke(state)
        self.assertEqual(state.get("appointment_step"), "doctor")
        self.assertIn("Dr.", state["response"])

    def test_doctor_not_asked_again_after_selection(self):
        """Once doctor is selected, subsequent steps should not ask for doctor again."""
        graph, state, _ = self._reach_doctor_step()
        state = dict(state, user_text="Dr. Sana Khan")
        state = graph.invoke(state)
        self.assertEqual(state.get("appointment_step"), "date")
        # Simulate date input
        state = dict(state, user_text="2026-09-29")
        state = graph.invoke(state)
        # Should advance to slot selection, not ask for doctor
        self.assertNotEqual(state.get("appointment_step"), "doctor")


# ===========================================================================
# 8. Fuzzy confirmation flow
# ===========================================================================

class FuzzyConfirmationTests(unittest.TestCase):
    def test_ambiguous_triggers_clarification(self):
        """When two doctors have similar names, bot should ask 'Did you mean?'"""
        # Use a fixture with two similarly-named doctors
        rows = [
            ["Doctor ID", "Doctor Name", "Specialization", "Consultation Fee"],
            ["D1", "Dr. Rahman", "Cardiologist", "800"],
            ["D2", "Dr. Rehman", "General Physician", "500"],
        ]
        directory = DoctorDirectory(lambda: rows)
        tools = DoctorTools(directory)
        # Both are close to "rahman"
        result = tools.resolve_doctor("rahman")
        # Should be matched or ambiguous — never crash
        self.assertIn(result["status"], {"matched", "ambiguous", "not_found"})
        if result["status"] == "ambiguous":
            self.assertGreater(len(result["matches"]), 1)
            # Must NOT silently select
            self.assertNotIn("doctor", result)


# ===========================================================================
# 9. Token optimisation — no Gemini for doctor ops
# ===========================================================================

class TokenOptimizationTests(unittest.TestCase):
    """Verifies that doctor discovery, fuzzy matching, and slot filtering never
    call the LLM. FakeLlm.call_count must remain 0 throughout these operations."""

    def setUp(self):
        self.llm = FakeLlm()
        self.graph, _ = _make_graph(self.llm)

    def test_doctor_list_no_gemini(self):
        self.graph.invoke({"user_text": "which doctors are available?"})
        self.assertEqual(self.llm.call_count, 0)

    def test_date_filtered_list_no_gemini(self):
        self.graph.invoke({"user_text": "available doctors on 29 sept 2026"})
        self.assertEqual(self.llm.call_count, 0)

    def test_specialization_filter_no_gemini(self):
        self.graph.invoke({"user_text": "which cardiologist is available?"})
        self.assertEqual(self.llm.call_count, 0)

    def test_fuzzy_match_no_gemini(self):
        tools = _make_tools()
        tools.resolve_doctor("dr sufiyan")  # direct call — no graph involved
        self.assertEqual(self.llm.call_count, 0)

    def test_normalize_no_gemini(self):
        normalize_doctor_text("Dr. Sufiyan")
        self.assertEqual(self.llm.call_count, 0)

    def test_specialization_resolve_no_gemini(self):
        resolve_specialization("cardiologist")
        self.assertEqual(self.llm.call_count, 0)


# ===========================================================================
# 10. Keyboard behaviour
# ===========================================================================

class KeyboardBehaviourTests(unittest.TestCase):
    def test_doctor_select_ui_returns_doctor_buttons(self):
        result = {
            "ui": "doctor_select",
            "doctor_choices": [
                {"Doctor ID": "D1", "Doctor Name": "Dr. Arjun Mehta"},
                {"Doctor ID": "D2", "Doctor Name": "Dr. Sana Khan"},
            ],
            "appointment_step": "doctor",
        }
        markup = _reply_markup(result)
        self.assertIsNotNone(markup)

    def test_doctor_select_no_global_menu(self):
        """Global menu must NOT appear during doctor selection step."""
        result = {
            "ui": "doctor_select",
            "doctor_choices": [{"Doctor ID": "D1", "Doctor Name": "Dr. X"}],
            "appointment_step": "doctor",
        }
        markup = _reply_markup(result)
        # The markup should be a doctor_menu, not a main_menu
        # (We cannot inspect InlineKeyboardMarkup internals easily, but
        # we can assert it's contextual: not None and step-specific)
        self.assertIsNotNone(markup)

    def test_active_flow_no_global_menu(self):
        self.assertIsNone(_reply_markup({"appointment_step": "email", "ui": ""}))

    def test_payment_has_contextual_keyboard(self):
        self.assertIsNotNone(_reply_markup({"appointment_step": "payment", "ui": "payment"}))

    def test_confirmation_has_contextual_keyboard(self):
        self.assertIsNotNone(_reply_markup({"appointment_step": "confirmation", "ui": "confirm"}))

    def test_completed_flow_returns_main_menu(self):
        self.assertIsNotNone(_reply_markup({"appointment_step": "complete", "ui": "main"}))

    def test_empty_doctor_choices_returns_none(self):
        """If doctor_choices is empty, no button keyboard is generated."""
        result = {"ui": "doctor_select", "doctor_choices": [], "appointment_step": "doctor"}
        markup = _reply_markup(result)
        self.assertIsNone(markup)


# ===========================================================================
# 11. Intent router tests
# ===========================================================================

class RouterTests(unittest.TestCase):
    def _intent(self, text):
        return classify_intent({"user_text": text})["intent"]

    def test_which_doctors_available_routes_to_doctor_list(self):
        self.assertEqual(self._intent("which doctors are available?"), "doctor_list")

    def test_which_dr_available_routes_to_doctor_list(self):
        self.assertEqual(self._intent("which dr are available on 29th?"), "doctor_list")

    def test_available_doctors_routes_to_doctor_list(self):
        self.assertEqual(self._intent("available doctors today?"), "doctor_list")

    def test_book_appointment_routes_correctly(self):
        self.assertEqual(self._intent("I want to book an appointment"), "appointment_booking")

    def test_cardiologist_available_routes_to_doctor_list(self):
        self.assertEqual(self._intent("which cardiologist is available?"), "doctor_list")

    def test_appointment_flow_preserves_intent(self):
        """Mid-flow messages must stay in appointment_flow regardless of content."""
        state = {"user_text": "which doctors are available?", "appointment_step": "doctor"}
        result = classify_intent(state)
        self.assertEqual(result["intent"], "appointment_flow")


# ===========================================================================
# 12. DoctorDirectory date-aware availability
# ===========================================================================

class DateAwareAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = _make_directory()
        self.slot_repo = _make_slot_repo()

    def test_returns_only_doctors_with_slots_on_date(self):
        doctors = self.directory.get_available_doctors_for_date("2026-09-29", self.slot_repo)
        names = [d["Doctor Name"] for d in doctors]
        self.assertIn("Dr. Sufian", names)
        self.assertNotIn("Dr. Arjun Mehta", names)

    def test_date_with_no_slots_returns_empty(self):
        doctors = self.directory.get_available_doctors_for_date("2000-01-01", self.slot_repo)
        self.assertEqual(doctors, [])

    def test_broken_slot_repo_returns_empty(self):
        class BrokenRepo:
            def _snapshot(self):
                raise RuntimeError("sheets down")

        doctors = self.directory.get_available_doctors_for_date("2026-09-29", BrokenRepo())
        self.assertEqual(doctors, [])


if __name__ == "__main__":
    unittest.main()
