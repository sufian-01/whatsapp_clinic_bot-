import unittest

from app.graph.graph import build_graph
from app.graph.nodes import GraphNodes


class FakeLlm:
    def answer(self, system_prompt, user_text, context):
        return f"answered:{user_text}:context={len(context)}"


class FakeRag:
    def search(self, question):
        return ["Clinic hours are 9 to 5."] if "hours" in question else []


class GraphTests(unittest.TestCase):
    def test_clinic_question_uses_rag_before_llm(self):
        graph = build_graph(GraphNodes("Test Clinic", FakeLlm(), FakeRag()))
        result = graph.invoke({"user_text": "What are the clinic hours?"})
        self.assertEqual(result["clinic_context"], ["Clinic hours are 9 to 5."])
        self.assertIn("context=1", result["response"])

    def test_general_question_skips_rag(self):
        graph = build_graph(GraphNodes("Test Clinic", FakeLlm(), FakeRag()))
        result = graph.invoke({"user_text": "Hello"})
        self.assertNotIn("clinic_context", result)
        self.assertIn("context=0", result["response"])