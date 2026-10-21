"""Tests for Gemini client multi-model resilience, quota exhaustion fallback, and friendly fallbacks."""

import unittest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage

from app.llm.gemini import GeminiClient, extract_text_from_content
from app.graph.nodes import GraphNodes


class GeminiResilienceTests(unittest.TestCase):
    def test_extract_text_from_content_string(self):
        self.assertEqual(extract_text_from_content("Hello world"), "Hello world")

    def test_extract_text_from_content_structured_list(self):
        content = [
            {"type": "text", "text": "Namaste! "},
            {"type": "text", "text": "How can I help you?"},
        ]
        self.assertEqual(extract_text_from_content(content), "Namaste! How can I help you?")

    def test_gemini_client_fallback_on_429_resource_exhausted(self):
        """When primary model encounters 429 quota exhausted, client automatically tries next candidate."""
        client = GeminiClient(api_key="test_api_key", model="gemini-2.5-flash")

        mock_exhausted = MagicMock()
        mock_exhausted.invoke.side_effect = Exception("429 RESOURCE_EXHAUSTED Quota exceeded for metric")

        mock_working = MagicMock()
        mock_working.invoke.return_value = AIMessage(content="Response from fallback model")

        def mock_create_model(model_name):
            if model_name == "gemini-2.5-flash":
                return mock_exhausted
            return mock_working

        with patch.object(client, "_create_model", side_effect=mock_create_model):
            client._model = mock_exhausted
            res = client.answer(system_prompt="sys", user_text="hi", context=["info"])
            self.assertEqual(res, "Response from fallback model")
            # Verify active model was switched to working candidate
            self.assertNotEqual(client._model_name, "gemini-2.5-flash")

    def test_node_answer_greeting_fallback_when_llm_down(self):
        """When LLM is completely down, 'hi' should return warm clinic welcome and welcome_menu."""
        mock_llm = MagicMock()
        mock_llm.answer.side_effect = RuntimeError("All LLM providers rate limited 429")

        nodes = GraphNodes(
            clinic_name="XYZ Super Clinic",
            support_phone="919876543210",
            llm=mock_llm,
            rag=MagicMock(),
            doctors=MagicMock(),
        )

        state = {
            "user_text": "hi",
            "intent": "greeting",
            "appointment_step": None,
            "welcome_menu_sent": False,
        }

        result = nodes.answer(state)
        self.assertIn("XYZ Super Clinic", result["response"])
        self.assertNotIn("unable to answer right now", result["response"].lower())
        self.assertEqual(result.get("ui"), "welcome_menu")

    def test_node_answer_general_query_fallback_when_llm_down(self):
        """When LLM is completely down, general query returns clinic assistance message with support phone."""
        mock_llm = MagicMock()
        mock_llm.answer.side_effect = RuntimeError("All LLM providers rate limited 429")

        nodes = GraphNodes(
            clinic_name="XYZ Super Clinic",
            support_phone="919876543210",
            llm=mock_llm,
            rag=MagicMock(),
            doctors=MagicMock(),
        )

        state = {
            "user_text": "hospital me konsi suvidha hai",
            "intent": "clinic_information",
            "appointment_step": None,
        }

        result = nodes.answer(state)
        self.assertIn("919876543210", result["response"])
        self.assertNotIn("unable to answer right now", result["response"].lower())


if __name__ == "__main__":
    unittest.main()
