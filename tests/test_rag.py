import tempfile
import unittest
from pathlib import Path

from app.rag.service import RagService


class RagTests(unittest.TestCase):
    def test_retrieves_matching_clinic_document(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "faq.md").write_text("The clinic is open on Monday.", encoding="utf-8")
            results = RagService(Path(directory)).search("When is the clinic open?")
        self.assertEqual(len(results), 1)

    def test_does_not_return_unrelated_document(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "faq.md").write_text("The clinic is open on Monday.", encoding="utf-8")
            results = RagService(Path(directory)).search("What is the parking policy?")
        self.assertEqual(results, [])