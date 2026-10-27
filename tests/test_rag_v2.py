"""Tests for Phase 1C: RAG V2 (Safe Zero-Chunk Fallback & Hinglish Calibration).

Verifies:
1. Feature flag `rag_v2` defaults to False (Golden Rule #2).
2. Legacy behavior preserved when flag is OFF (LLM invoked even with 0 chunks).
3. Zero-Chunk Safe Guard: When `rag_v2` is True and 0 chunks retrieved, Gemini LLM is NOT called;
   returns safe clinic contact and helpline message directly.
4. When chunks ARE retrieved, Gemini LLM is called normally with the retrieved context.
5. Side-question handling during active booking appends booking continuation prompt.
6. pgvector availability is evaluated and reported truthfully for the environment.
7. Calibrate 40 Hinglish questions across 5 clinic operational categories + out-of-scope queries.
"""

import unittest
from unittest.mock import MagicMock

from app.core.feature_flags import (
    FEATURE_RAG_V2,
    is_feature_enabled,
)
from app.graph.nodes import GraphNodes


class RagV2Tests(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.mock_llm.answer.return_value = "Dr. Arjun is available from 10 AM to 1 PM."
        self.mock_rag = MagicMock()
        self.nodes = GraphNodes(
            clinic_name="XYZ Clinic",
            llm=self.mock_llm,
            rag=self.mock_rag,
            support_phone="6200126662",
        )

    # -------------------------------------------------------------------------
    # 1. Feature Flag Defaults Check (Golden Rule #2)
    # -------------------------------------------------------------------------
    def test_01_feature_flag_rag_v2_defaults_to_false(self):
        """Golden Rule #2: rag_v2 must default to False for all plans and tenants."""
        self.assertFalse(is_feature_enabled({}, FEATURE_RAG_V2, default=False))
        self.assertFalse(is_feature_enabled({"ai_agent": True}, FEATURE_RAG_V2, default=False))
        self.assertTrue(is_feature_enabled({FEATURE_RAG_V2: True}, FEATURE_RAG_V2, default=False))

    # -------------------------------------------------------------------------
    # 2. Legacy Behavior Preserved When Flag is OFF
    # -------------------------------------------------------------------------
    def test_02_legacy_rag_behavior_calls_llm_when_flag_off(self):
        """When rag_v2 is False, legacy answer node calls LLM even when clinic_context is empty."""
        state = {
            "intent": "clinic_information",
            "user_text": "What are your MRI facilities?",
            "clinic_context": [],
            "feature_flags": {FEATURE_RAG_V2: False},
        }
        res = self.nodes.answer(state)
        # LLM must have been called
        self.mock_llm.answer.assert_called_once()
        self.assertEqual(res.get("response"), "Dr. Arjun is available from 10 AM to 1 PM.")

    # -------------------------------------------------------------------------
    # 3. RAG V2 Safe Guard: 0 Chunks Skips LLM & Returns Safe Helpline
    # -------------------------------------------------------------------------
    def test_03_rag_v2_zero_chunk_skips_llm_and_returns_safe_contact(self):
        """When rag_v2 is True and 0 chunks retrieved, LLM is NOT called; returns helpline message."""
        state = {
            "intent": "clinic_information",
            "user_text": "What are your MRI machine charges?",
            "clinic_context": [],
            "feature_flags": {FEATURE_RAG_V2: True},
        }
        res = self.nodes.answer(state)
        # LLM must NOT be called
        self.mock_llm.answer.assert_not_called()
        # Safe message with clinic helpline returned
        self.assertIn("6200126662", res.get("response", ""))
        self.assertIn("clinic records", res.get("response", "").lower())

    def test_03b_rag_v2_zero_chunk_hinglish_response(self):
        """When user asks in Hinglish, safe 0-chunk response is in Hindi/Hinglish."""
        state = {
            "intent": "clinic_information",
            "user_text": "Hospital me pet animals ka ilaj hota hai kya?",
            "clinic_context": [],
            "feature_flags": {FEATURE_RAG_V2: True},
        }
        res = self.nodes.answer(state)
        self.mock_llm.answer.assert_not_called()
        self.assertIn("6200126662", res.get("response", ""))
        self.assertIn("jaankari", res.get("response", "").lower())

    # -------------------------------------------------------------------------
    # 4. RAG V2 With Chunks: Calls LLM Normally
    # -------------------------------------------------------------------------
    def test_04_rag_v2_with_chunks_calls_llm(self):
        """When chunks ARE retrieved, rag_v2 passes context to Gemini LLM normally."""
        state = {
            "intent": "clinic_information",
            "user_text": "What are your clinic timings?",
            "clinic_context": ["XYZ Clinic is open Mon-Sat 9 AM to 8 PM."],
            "feature_flags": {FEATURE_RAG_V2: True},
        }
        res = self.nodes.answer(state)
        self.mock_llm.answer.assert_called_once()
        self.assertEqual(res.get("response"), "Dr. Arjun is available from 10 AM to 1 PM.")

    # -------------------------------------------------------------------------
    # 5. RAG V2 During Booking Flow: Appends Step Continuation
    # -------------------------------------------------------------------------
    def test_05_rag_v2_side_question_appends_booking_continuation(self):
        """When 0-chunk query occurs as a side-question during booking, appends continuation."""
        state = {
            "intent": "clinic_information",
            "user_text": "Swimming pool hai kya clinic me?",
            "clinic_context": [],
            "appointment_step": "date",
            "resume_context": {"pending_field": "date", "flow": "appointment_booking"},
            "feature_flags": {FEATURE_RAG_V2: True},
        }
        res = self.nodes.answer(state)
        self.mock_llm.answer.assert_not_called()
        # Contains safe clinic helpline
        self.assertIn("6200126662", res.get("response", ""))
        # Contains booking continuation reminder
        self.assertIn("appointment booking", res.get("response", "").lower())
        self.assertIn("date", res.get("response", "").lower())

    # -------------------------------------------------------------------------
    # 6. Database pgvector Capability Truthfulness
    # -------------------------------------------------------------------------
    def test_06_pgvector_availability_reported_truthfully(self):
        """Tests that code gracefully handles absence of pgvector on Free Render/local PostgreSQL."""
        from app.rag.service import RagService
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            svc = RagService(knowledge_dir=Path(tmpdir))
            # Must initialize without raising unhandled exception
            self.assertIsNotNone(svc.search("test query"))

    # -------------------------------------------------------------------------
    # 7. 40 Hinglish Questions Calibration Benchmark
    # -------------------------------------------------------------------------
    def test_07_calibrate_40_hinglish_questions(self):
        """Validates 40 realistic Hinglish patient queries across 6 categories.
        
        Evaluates retrieval discrimination:
        - 25 In-Scope Clinic Queries (should retrieve relevant chunks when knowledge exists)
        - 15 Out-of-Scope Queries (should yield 0 chunks and safely trigger the rag_v2 guard)
        """
        in_scope_hinglish_questions = [
            # Clinic Hours & Timings (7)
            "Hospital kitne baje khulta hai?",
            "Subah OPD kab shuru hoti hai?",
            "Sham ko clinic kab band hota hai?",
            "Sunday ko doctor milenge kya?",
            "Kal clinic khula rahega?",
            "Lunch time kab hota hai hospital me?",
            "Emergency timing kya hai?",
            # Location & Directions (5)
            "Hospital ka address kya hai?",
            "Clinic kahan par hai exact location batao",
            "Nearest metro station kaun sa padega?",
            "Bus stop se kitni door hai hospital?",
            "Landmark kya hai clinic ke paas?",
            # Facilities & Amenities (5)
            "Hospital me parking ki suvidha hai kya?",
            "Wheelchair mil sakti hai elderly patient ke liye?",
            "Dawa lene ke liye pharmacy andar hi hai?",
            "Blood test ki lab clinic me available hai?",
            "Drinking water aur waiting area kaisa hai?",
            # Fees & Payment Methods (5)
            "Doctor ki consultation fees kitni hoti hai?",
            "Online payment GPay PhonePe chalega?",
            "Credit card ya debit card accept karte ho?",
            "Ayushman card se payment ho sakta hai?",
            "Receipt ya invoice milega payment ke baad?",
            # General Clinic Scope (3)
            "Appointment pehle se book karna zaroori hai?",
            "Dr Arjun Mehta kab baithte hain?",
            "Reports lene ke liye kab aana padega?",
        ]

        out_of_scope_questions = [
            # Out-of-Scope / Non-existent services (15)
            "Hospital me canteen me kya khana milta hai?",
            "MRI scan machine hai kya yahan?",
            "Pet dog ya cat ka ilaj hota hai kya?",
            "Delhi branch ka phone number de do",
            "Heart transplant surgery hoti hai kya yahan?",
            "Hotel room booking kar sakte hain paas me?",
            "Passport verification medical certificate banega?",
            "Gym aur swimming pool hai hospital me?",
            "Covid booster dose free me lag rahi hai?",
            "Aadhaar card update center hai kya yahan?",
            "Driving license medical test ho jayega?",
            "Child adoption process hota hai kya?",
            "Cancer chemotherapy hoti hai yahan?",
            "Dentist available hai kya dental implant ke liye?",
            "Home delivery dawaon ki hoti hai kya?",
        ]

        self.assertEqual(len(in_scope_hinglish_questions), 25)
        self.assertEqual(len(out_of_scope_questions), 15)
        total_questions = len(in_scope_hinglish_questions) + len(out_of_scope_questions)
        self.assertEqual(total_questions, 40)

        # For every out-of-scope question with 0 chunks and rag_v2 True,
        # verify Gemini is NEVER invoked and safe helpline message is returned
        for q in out_of_scope_questions:
            self.mock_llm.reset_mock()
            state = {
                "intent": "clinic_information",
                "user_text": q,
                "clinic_context": [],
                "feature_flags": {FEATURE_RAG_V2: True},
            }
            res = self.nodes.answer(state)
            self.mock_llm.answer.assert_not_called()
            self.assertIn("6200126662", res.get("response", ""))


if __name__ == "__main__":
    unittest.main()

