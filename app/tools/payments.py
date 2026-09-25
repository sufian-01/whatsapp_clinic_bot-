"""Payment boundary; online payments intentionally remain unimplemented."""

from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode

import qrcode


class PaymentTools:
    def create_online_payment(self, amount: str) -> dict:
        return {"success": False, "status": "NOT_IMPLEMENTED", "message": "Online payment will be available soon."}

    def verify_payment_status(self, payment_id: str) -> dict:
        return {"success": False, "status": "NOT_IMPLEMENTED", "payment_id": payment_id}

    def record_offline_payment(self, amount: str) -> dict:
        return {"success": True, "payment_method": "Offline", "payment_status": "Pending", "amount": amount}

    def get_payment_status(self, payment_id: str) -> dict:
        return {"success": False, "status": "UNKNOWN", "payment_id": payment_id}

    def generate_offline_upi_qr(self, amount: str, clinic_name: str, reference: str, output_dir: Path) -> dict:
        try:
            numeric_amount = Decimal(str(amount).replace(",", "").replace("₹", "").strip())
            if numeric_amount <= 0:
                raise InvalidOperation
            upi_id = "khansyrian1@okhdfcbank"
            uri = "upi://pay?" + urlencode({"pa": upi_id, "pn": clinic_name, "am": f"{numeric_amount:.2f}", "cu": "INR", "tr": reference})
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / f"{reference}-upi.png"
            qrcode.make(uri).save(path)
            return {"success": True, "upi_id": upi_id, "amount": float(numeric_amount), "qr_path": str(path), "upi_uri": uri}
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "error_code": "INVALID_AMOUNT", "message": "A valid consultation amount is required."}