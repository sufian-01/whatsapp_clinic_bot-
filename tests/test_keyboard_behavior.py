import unittest

from app.telegram.handlers import _reply_markup


class KeyboardBehaviorTests(unittest.TestCase):
    def test_active_flow_has_no_global_menu(self):
        self.assertIsNone(_reply_markup({"appointment_step": "email", "ui": ""}))

    def test_payment_and_confirmation_have_contextual_keyboards(self):
        self.assertIsNotNone(_reply_markup({"appointment_step": "payment", "ui": "payment"}))
        self.assertIsNotNone(_reply_markup({"appointment_step": "confirmation", "ui": "confirm"}))

    def test_completed_flow_returns_main_menu(self):
        self.assertIsNotNone(_reply_markup({"appointment_step": "complete", "ui": "main"}))