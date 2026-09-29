import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import gmail_tools
from app.graph.nodes import GraphNodes
from app.tools.gmail import GmailTools
from app.tools.patients import PatientRecord


class FakeSendRequest:
    def execute(self):
        return {"id": "message-1"}


class FakeMessages:
    def send(self, **kwargs):
        self.payload = kwargs
        return FakeSendRequest()


class FakeUsers:
    def __init__(self):
        self.messages_api = FakeMessages()

    def messages(self):
        return self.messages_api


class FakeGmailService:
    def __init__(self):
        self.users_api = FakeUsers()

    def users(self):
        return self.users_api


class FakePatients:
    def __init__(self):
        self.created = []

    def create_patient(self, record):
        self.created.append(record)
        return {"success": True, "patient": record}

    def generate_patient_id(self):
        return {"patient_id": "PAT-TEST"}

    def generate_token(self):
        return {"token_no": "TKN-0099"}


class FakePayments:
    def record_offline_payment(self, amount):
        return {"success": True, "payment_method": "Offline", "payment_status": "Pending", "amount": amount}

    def generate_offline_upi_qr(self, amount, clinic_name, token_no, output_dir):
        return {"success": True, "qr_path": "data/invoices/fake-qr.png"}


class FakeInvoices:
    def generate_invoice(self, invoice_data, output_dir):
        return {"success": True, "invoice_number": "INV-TEST-001", "file_path": "data/invoices/fake-invoice.pdf"}


class EmailTests(unittest.TestCase):
    def test_attachment_sender_uses_gmail_service(self):
        with tempfile.TemporaryDirectory() as directory:
            attachment = Path(directory, "invoice.pdf")
            attachment.write_bytes(b"pdf")
            service = FakeGmailService()
            with patch.object(gmail_tools, "gmail_service", service):
                result = gmail_tools.send_email_with_attachment.invoke({
                    "to": "patient@example.com",
                    "subject": "Invoice",
                    "body": "Pending",
                    "attachment_path": str(attachment),
                })
            self.assertEqual(result, "Email sent successfully.")
            self.assertIn("raw", service.users_api.messages_api.payload["body"])

    def test_attachment_sender_propagates_provider_failure(self):
        class FailingMessages(FakeMessages):
            def send(self, **kwargs):
                raise RuntimeError("gmail unavailable")

        service = FakeGmailService()
        service.users_api.messages_api = FailingMessages()
        with tempfile.TemporaryDirectory() as directory:
            attachment = Path(directory, "invoice.pdf")
            attachment.write_bytes(b"pdf")
            with patch.object(gmail_tools, "gmail_service", service):
                with self.assertRaises(RuntimeError):
                    gmail_tools.send_email_with_attachment.invoke({
                        "to": "patient@example.com",
                        "subject": "Invoice",
                        "body": "Pending",
                        "attachment_path": str(attachment),
                    })

    def test_gmail_tools_send_invoice_email_success(self):
        """GmailTools returns success dict when sender succeeds."""
        mock_sender = MagicMock(return_value="Email sent successfully.")
        tool = GmailTools(mock_sender)
        result = tool.send_invoice_email(
            recipient="patient@example.com",
            invoice_number="INV-001",
            subject="Invoice Subject",
            body="Invoice Body",
            file_path="/tmp/fake_invoice.pdf",
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["email_sent"])
        self.assertEqual(result["recipient"], "patient@example.com")
        self.assertEqual(result["invoice_number"], "INV-001")
        mock_sender.assert_called_once_with(
            "patient@example.com",
            "Invoice Subject",
            "Invoice Body",
            "/tmp/fake_invoice.pdf",
        )

    def test_gmail_tools_send_invoice_email_failure_handled(self):
        """GmailTools catches exceptions and returns error dict without crashing."""
        def failing_sender(*args, **kwargs):
            raise RuntimeError("Gmail API rate limit exceeded")

        tool = GmailTools(failing_sender)
        result = tool.send_invoice_email(
            recipient="patient@example.com",
            invoice_number="INV-001",
            subject="Invoice Subject",
            body="Invoice Body",
            file_path="/tmp/fake_invoice.pdf",
        )
        self.assertFalse(result["success"])
        self.assertFalse(result["email_sent"])
        self.assertEqual(result["error_code"], "GMAIL_SEND_FAILED")

    def test_booking_completes_and_sends_invoice_email(self):
        """Successful offline booking triggers invoice generation and email delivery."""
        mock_gmail = MagicMock()
        mock_gmail.send_invoice_email.return_value = {
            "success": True,
            "email_sent": True,
            "recipient": "patient@example.com",
            "invoice_number": "INV-TEST-001",
        }

        nodes = GraphNodes(
            clinic_name="Test Clinic",
            llm=None,
            rag=None,
            patients=FakePatients(),
            payments=FakePayments(),
            invoices=FakeInvoices(),
            gmail=mock_gmail,
        )

        initial_state = {
            "token_no": "TKN-0099",
            "patient_id": "PAT-TEST",
            "patient_name": "John Doe",
            "patient_phone": "+919876543210",
            "patient_email": "patient@example.com",
            "doctor_name": "Dr. Sufian",
            "specialization": "Cardiologist",
            "appointment_date": "2026-09-29",
            "appointment_time": "09:00",
            "amount": "800",
            "slot_id": "S1",
        }

        final_state = nodes._complete_offline(initial_state)

        # Verified: booking is confirmed, invoice sent, email_sent is True
        self.assertEqual(final_state["booking_status"], "Confirmed")
        self.assertEqual(final_state["token_no"], "TKN-0099")
        self.assertTrue(final_state["email_sent"])
        self.assertIn("sent to your email", final_state["response"])
        mock_gmail.send_invoice_email.assert_called_once()

    def test_booking_preserves_confirmed_status_when_gmail_fails(self):
        """When Gmail delivery fails, booking is NOT lost and token remains confirmed."""
        mock_gmail = MagicMock()
        mock_gmail.send_invoice_email.return_value = {
            "success": False,
            "email_sent": False,
            "error_code": "GMAIL_SEND_FAILED",
        }

        nodes = GraphNodes(
            clinic_name="Test Clinic",
            llm=None,
            rag=None,
            patients=FakePatients(),
            payments=FakePayments(),
            invoices=FakeInvoices(),
            gmail=mock_gmail,
        )

        initial_state = {
            "token_no": "TKN-0099",
            "patient_id": "PAT-TEST",
            "patient_name": "John Doe",
            "patient_phone": "+919876543210",
            "patient_email": "patient@example.com",
            "doctor_name": "Dr. Sufian",
            "specialization": "Cardiologist",
            "appointment_date": "2026-09-29",
            "appointment_time": "09:00",
            "amount": "800",
            "slot_id": "S1",
        }

        final_state = nodes._complete_offline(initial_state)

        # Verified: confirmed booking is preserved despite Gmail failure
        self.assertEqual(final_state["booking_status"], "Confirmed")
        self.assertEqual(final_state["token_no"], "TKN-0099")
        self.assertFalse(final_state["email_sent"])
        self.assertIn("email delivery failed", final_state["response"])
        self.assertIn("Appointment confirmed", final_state["response"])


if __name__ == "__main__":
    unittest.main()