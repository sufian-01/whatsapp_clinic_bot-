import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import gmail_tools


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


class EmailTests(unittest.TestCase):
    def test_attachment_sender_uses_gmail_service(self):
        with tempfile.TemporaryDirectory() as directory:
            attachment = Path(directory, "invoice.pdf")
            attachment.write_bytes(b"pdf")
            service = FakeGmailService()
            with patch.object(gmail_tools, "gmail_service", service):
                result = gmail_tools.send_email_with_attachment.invoke({"to": "patient@example.com", "subject": "Invoice", "body": "Pending", "attachment_path": str(attachment)})
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
                    gmail_tools.send_email_with_attachment.invoke({"to": "patient@example.com", "subject": "Invoice", "body": "Pending", "attachment_path": str(attachment)})