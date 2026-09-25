import unittest

from app.tools.appointments import AppointmentTools
from app.tools.payments import PaymentTools


class ToolContractsTests(unittest.TestCase):
    def test_booking_requires_token(self):
        tool = AppointmentTools(object())
        result = tool.book_slot("S1", "PAT-1", "")
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "TOKEN_REQUIRED")

    def test_appointment_tool_reports_repository_failure(self):
        class BrokenRepository:
            def get_available_slots(self, doctor, date):
                raise RuntimeError("sheets unavailable")

        result = AppointmentTools(BrokenRepository()).get_available_slots("Doctor", "2026-09-28")
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "SLOT_READ_FAILED")

    def test_online_payment_is_not_implemented(self):
        result = PaymentTools().create_online_payment("700")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "NOT_IMPLEMENTED")

    def test_offline_payment_is_pending(self):
        result = PaymentTools().record_offline_payment("700")
        self.assertTrue(result["success"])
        self.assertEqual(result["payment_status"], "Pending")