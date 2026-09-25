import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.tools.payments import PaymentTools


class PaymentQrTests(unittest.TestCase):
    def test_qr_contains_exact_upi_details(self):
        with tempfile.TemporaryDirectory() as directory:
            result = PaymentTools().generate_offline_upi_qr("₹500", "XYZ Clinic", "TKN-0001", Path(directory))
            self.assertTrue(result["success"])
            self.assertTrue(Path(result["qr_path"]).exists())
            query = parse_qs(urlparse(result["upi_uri"]).query)
            self.assertEqual(query["pa"], ["khansyrian1@okhdfcbank"])
            self.assertEqual(query["am"], ["500.00"])
            self.assertEqual(query["cu"], ["INR"])

    def test_invalid_amount_is_rejected(self):
        result = PaymentTools().generate_offline_upi_qr("", "XYZ Clinic", "TKN-0001", Path(tempfile.mkdtemp()))
        self.assertFalse(result["success"])