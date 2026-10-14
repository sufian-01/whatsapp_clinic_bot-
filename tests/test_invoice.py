import tempfile
import unittest
from pathlib import Path

from app.tools.invoice import InvoiceData, generate_invoice
from app.tools.payments import PaymentTools
from pypdf import PdfReader


class InvoiceTests(unittest.TestCase):
    def test_generates_pending_offline_invoice(self):
        with tempfile.TemporaryDirectory() as directory:
            qr = PaymentTools(upi_id="clinic@upi").generate_offline_upi_qr("700", "Test Clinic", "TKN-0001", Path(directory))
            number, path = generate_invoice(InvoiceData("Test Clinic", "000", "", "", "Patient", "patient@example.com", "000", "Dr. Test", "Physician", "2026-09-28", "10:00", "TKN-0001", "700", "Pay at Clinic / UPI", "Pending", qr["qr_path"], upi_id="clinic@upi"), Path(directory))
            self.assertTrue(number.startswith("INV-"))
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 0)
            text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
            self.assertIn("Pending", text)
            self.assertIn("clinic@upi", text)
            self.assertNotIn("khansyrian1@okhdfcbank", text)
            self.assertNotIn("Paid", text)