import tempfile
import unittest
from pathlib import Path

from app.tools.invoice import InvoiceData, generate_invoice


class InvoiceTests(unittest.TestCase):
    def test_generates_pending_offline_invoice(self):
        with tempfile.TemporaryDirectory() as directory:
            number, path = generate_invoice(InvoiceData("Test Clinic", "000", "", "", "Patient", "patient@example.com", "000", "Dr. Test", "Physician", "2026-09-28", "10:00", "TKN-0001", "700", "Pay at Clinic", "Pending"), Path(directory))
            self.assertTrue(number.startswith("INV-"))
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 0)