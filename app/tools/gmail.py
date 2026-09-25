"""Structured Gmail invoice delivery tool using the existing Gmail foundation."""


class GmailTools:
    def __init__(self, sender) -> None:
        self._sender = sender

    def send_invoice_email(self, recipient: str, invoice_number: str, subject: str, body: str, file_path: str) -> dict:
        try:
            self._sender(recipient, subject, body, file_path)
            return {"success": True, "email_sent": True, "recipient": recipient, "invoice_number": invoice_number}
        except Exception:
            return {"success": False, "email_sent": False, "recipient": recipient, "invoice_number": invoice_number, "error_code": "GMAIL_SEND_FAILED"}