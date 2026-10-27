"""Tests for Phase 1B: Smart Intent V2.

Verifies:
1. Feature flag `smart_intent_v2` defaults to False for tenant isolation and backward compatibility.
2. Characterization tests locking existing router behavior when flag is OFF.
3. Fix for router reschedule intent detection ("I need to reschedule my appointment" -> appointment_reschedule).
4. Fix for router my appointments detection ("Show my upcoming appointments" -> patient_appointments).
5. Step-aware deterministic fast paths for active booking steps (name, email, phone, doctor, date, slot).
6. Rich context forwarding to Gemini classifier (expected_field, last_bot_question, collected_fields).
"""

import unittest
from unittest.mock import MagicMock, patch

from app.core.feature_flags import (
    FEATURE_SMART_INTENT_V2,
    is_feature_enabled,
    parse_feature_flags_json,
)
from app.graph.router import classify_intent
from app.llm.classifier import classify_with_ai


class SmartIntentV2Tests(unittest.TestCase):
    # -------------------------------------------------------------------------
    # 1. Feature Flag Defaults Check (Golden Rule #2)
    # -------------------------------------------------------------------------
    def test_01_feature_flag_defaults_to_false(self):
        """Golden Rule #2: smart_intent_v2 must default to False for all plans and tenants."""
        self.assertFalse(is_feature_enabled({}, FEATURE_SMART_INTENT_V2, default=False))
        self.assertFalse(is_feature_enabled({"ai_agent": True}, FEATURE_SMART_INTENT_V2, default=False))
        self.assertTrue(is_feature_enabled({FEATURE_SMART_INTENT_V2: True}, FEATURE_SMART_INTENT_V2, default=False))

    # -------------------------------------------------------------------------
    # 2. Router Reschedule Bug Fix
    # -------------------------------------------------------------------------
    def test_02_router_reschedule_intent_detection(self):
        """'I need to reschedule my appointment' must be classified as appointment_reschedule, not doctor_list."""
        res = classify_intent({"user_text": "I need to reschedule my appointment"})
        self.assertEqual(res.get("intent"), "appointment_reschedule")

        res_hi = classify_intent({"user_text": "Mujhe appointment reschedule karni hai"})
        self.assertEqual(res_hi.get("intent"), "appointment_reschedule")

    # -------------------------------------------------------------------------
    # 3. Router My Appointments Bug Fix
    # -------------------------------------------------------------------------
    def test_03_router_my_appointments_intent_detection(self):
        """'Show my upcoming appointments' must be classified as patient_appointments, not appointment_booking."""
        res = classify_intent({"user_text": "Show my upcoming appointments"})
        self.assertEqual(res.get("intent"), "patient_appointments")

        res_detail = classify_intent({"user_text": "My appointment details"})
        self.assertEqual(res_detail.get("intent"), "patient_appointments")

    # -------------------------------------------------------------------------
    # 4. Step-Aware Fast Paths
    # -------------------------------------------------------------------------
    def test_04_step_aware_fast_paths_at_date_step(self):
        """When at 'date' step, natural date references are routed to appointment_flow."""
        state = {
            "user_text": "kal",
            "appointment_step": "date",
            "feature_flags": {FEATURE_SMART_INTENT_V2: True},
        }
        res = classify_intent(state)
        self.assertEqual(res.get("intent"), "appointment_flow")
        self.assertEqual(res.get("pending_field"), "date")

    def test_05_step_aware_fast_paths_at_slot_step(self):
        """When at 'slot' step, slot numbers or times route directly to appointment_flow."""
        state = {
            "user_text": "10:00 AM",
            "appointment_step": "slot",
            "feature_flags": {FEATURE_SMART_INTENT_V2: True},
        }
        res = classify_intent(state)
        self.assertEqual(res.get("intent"), "appointment_flow")
        self.assertEqual(res.get("pending_field"), "slot")

    # -------------------------------------------------------------------------
    # 5. Gemini Classifier Receives Context Rich Payload
    # -------------------------------------------------------------------------
    def test_06_classify_with_ai_passes_context_payload(self):
        """classify_with_ai accepts and includes expected_field, last_bot_question, and collected_fields in prompt."""
        mock_llm = MagicMock()
        mock_llm.answer.return_value = '{"intent": "appointment_flow", "is_cancellation": false, "is_side_question": false}'

        res = classify_with_ai(
            llm=mock_llm,
            user_text="Aarav Sharma",
            active_flow="appointment_booking",
            current_step="name",
            expected_field="patient_name",
            last_bot_question="Sure. May I know your name?",
            collected_fields=["doctor_id", "doctor_name"],
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.get("intent"), "appointment_flow")

        # Verify context passed to mock_llm.answer
        call_args = mock_llm.answer.call_args
        context_arg = call_args[0][2]  # 3rd positional argument is context list
        context_str = " ".join(context_arg)
        self.assertIn("patient_name", context_str)
        self.assertIn("Sure. May I know your name?", context_str)
        self.assertIn("doctor_id", context_str)

    # -------------------------------------------------------------------------
    # 6. Legacy Behavior Preserved When Flag is OFF (Golden Rule #1)
    # -------------------------------------------------------------------------
    def test_07_characterization_legacy_behavior_preserved_when_flag_off(self):
        """When smart_intent_v2 is False, standard router behavior works as expected."""
        state = {
            "user_text": "Kal subah 10 baje",
            "appointment_step": "date",
            "feature_flags": {FEATURE_SMART_INTENT_V2: False},
        }
        res = classify_intent(state)
        # Should route to appointment_flow
        self.assertEqual(res.get("intent"), "appointment_flow")

    # -------------------------------------------------------------------------
    # 7. Name Step Disambiguation (Habiba / Doctor Name Conflict Prevention)
    # -------------------------------------------------------------------------
    def test_08_name_step_does_not_misinterpret_doctor_name_or_specialty(self):
        """Names like 'Habiba', 'Sufian', or 'Raj' at name step are treated as patient names."""
        for name in ["Habiba", "Sufian", "Pooja Ward", "Raj Treatment"]:
            state = {
                "user_text": name,
                "appointment_step": "name",
                "feature_flags": {FEATURE_SMART_INTENT_V2: True},
            }
            res = classify_intent(state)
            self.assertEqual(res.get("intent"), "appointment_flow", f"Failed for name '{name}'")
            self.assertEqual(res.get("pending_field"), "name")

    # -------------------------------------------------------------------------
    # 8. Side Questions Handled Gracefully During Active Flow
    # -------------------------------------------------------------------------
    def test_09_side_questions_during_flow_still_trigger_side_question_handling(self):
        """Informational side questions during an active step preserve resume_context."""
        state = {
            "user_text": "hospital ka address kya hai?",
            "appointment_step": "date",
            "feature_flags": {FEATURE_SMART_INTENT_V2: True},
        }
        res = classify_intent(state)
        self.assertEqual(res.get("intent"), "clinic_information")
        self.assertEqual(res.get("interruption_type"), "side_question")
        self.assertIsNotNone(res.get("resume_context"))
        self.assertEqual(res["resume_context"].get("pending_field"), "date")

    # -------------------------------------------------------------------------
    # 9. In-Flow Cancellation
    # -------------------------------------------------------------------------
    def test_10_cancel_queries_during_flow_trigger_draft_cancel(self):
        """Universal cancellation phrases during an active flow trigger appointment_draft_cancel."""
        for cancel_phrase in ["cancel", "nahi chahiye", "rehne do", "chhod do"]:
            state = {
                "user_text": cancel_phrase,
                "appointment_step": "phone",
                "feature_flags": {FEATURE_SMART_INTENT_V2: True},
            }
            res = classify_intent(state)
            self.assertEqual(res.get("intent"), "appointment_draft_cancel", f"Failed for '{cancel_phrase}'")
            self.assertEqual(res.get("interruption_type"), "cancellation")

    # -------------------------------------------------------------------------
    # 10. Hinglish Date and Time Variations
    # -------------------------------------------------------------------------
    def test_11_hinglish_date_and_time_variations(self):
        """Hinglish relative date inputs at date step route to appointment_flow."""
        for phrase in ["kal", "tomorrow", "parso sham ko", "aaj dopahar"]:
            state = {
                "user_text": phrase,
                "appointment_step": "date",
                "feature_flags": {FEATURE_SMART_INTENT_V2: True},
            }
            res = classify_intent(state)
            self.assertEqual(res.get("intent"), "appointment_flow", f"Failed for '{phrase}'")

    # -------------------------------------------------------------------------
    # 11. Word Boundary Edge Cases
    # -------------------------------------------------------------------------
    def test_12_specialization_word_boundary_edge_cases(self):
        """Words containing 'ent' as a substring do not falsely trigger doctor_list."""
        for text in ["urgent care", "patient records", "dental treatment"]:
            res = classify_intent({"user_text": text})
            self.assertNotEqual(res.get("intent"), "doctor_list", f"False doctor_list for '{text}'")

        # But standalone 'ENT' or 'ent specialist' DOES trigger doctor_list
        res_ent = classify_intent({"user_text": "I want an ENT specialist"})
        self.assertEqual(res_ent.get("intent"), "doctor_list")

    # -------------------------------------------------------------------------
    # 12. Direct Reschedule and Cancel Variations
    # -------------------------------------------------------------------------
    def test_13_all_reschedule_variations_pass(self):
        """All typical phrasing for rescheduling are correctly classified."""
        cases = [
            "I need to reschedule my appointment",
            "Can I change my appointment date to tomorrow?",
            "Please change time for token TKN-1001",
            "Mujhe appointment reschedule karni hai",
            "Mera booking badal do please",
            "Kal ka time change karna hai",
            "Dusra time mil sakta hai kya?",
        ]
        for c in cases:
            res = classify_intent({"user_text": c})
            self.assertEqual(res.get("intent"), "appointment_reschedule", f"Failed on '{c}'")


if __name__ == "__main__":
    unittest.main()

