"""Structured invoice generation tool."""

from .invoice import generate_invoice


class InvoiceTools:
    def generate_invoice(self, data, output_dir):
        try:
            number, path = generate_invoice(data, output_dir)
            return {"success": True, "invoice_number": number, "file_path": str(path)}
        except Exception:
            return {"success": False, "error_code": "INVOICE_GENERATION_FAILED"}