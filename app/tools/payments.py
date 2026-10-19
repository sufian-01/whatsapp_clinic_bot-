"""Payment boundary: Razorpay online payments and offline UPI QR tracking."""

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import qrcode

from ..services.razorpay_service import RazorpayService


class PaymentTools:
    def __init__(
        self,
        upi_id: str = "",
        razorpay_key_id: str = "",
        razorpay_key_secret: str = "",
        razorpay_service: Optional[RazorpayService] = None,
    ) -> None:
        self._upi_id = upi_id
        self._razorpay_key_id = razorpay_key_id
        self._razorpay_key_secret = razorpay_key_secret
        self._razorpay = razorpay_service or RazorpayService(
            default_key_id=razorpay_key_id,
            default_key_secret=razorpay_key_secret,
            default_upi_id=upi_id,
        )
        self._payments_store: Dict[str, Dict[str, Any]] = {}

    @property
    def upi_id(self) -> str:
        return self._upi_id

    def create_online_payment(
        self,
        amount: str,
        clinic_name: str = "Clinic",
        patient_name: str = "Patient",
        patient_phone: str = "",
        appointment_id: str = "",
        doctor_name: str = "",
        tenant_id: str = "default",
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        upi_id: Optional[str] = None,
    ) -> dict:
        """Create a Razorpay payment link and UPI deep link for consultation."""
        res = self._razorpay.create_payment(
            amount=amount,
            clinic_name=clinic_name,
            patient_name=patient_name,
            patient_phone=patient_phone,
            appointment_id=appointment_id,
            doctor_name=doctor_name,
            key_id=key_id or self._razorpay_key_id,
            key_secret=key_secret or self._razorpay_key_secret,
            upi_id=upi_id or self._upi_id,
            tenant_id=tenant_id,
        )
        pid = res.get("payment_id")
        res["payment_status"] = res.get("status", "Pending")
        if pid:
            self._payments_store[pid] = dict(res)
        return res

    def verify_payment_status(self, payment_id: str) -> dict:
        pay = self._payments_store.get(payment_id)
        if pay:
            return {"success": True, "status": pay.get("status", "Pending"), "payment_id": payment_id}
        return {"success": False, "status": "UNKNOWN", "payment_id": payment_id}

    def record_offline_payment(self, amount: str) -> dict:
        return {"success": True, "payment_method": "Offline", "payment_status": "Pending", "amount": amount}

    def get_payment_status(self, payment_id: str) -> dict:
        return self.verify_payment_status(payment_id)

    def mark_payment_paid(self, payment_id: str, transaction_ref: str = "") -> dict:
        pay = self._payments_store.get(payment_id)
        if pay:
            pay["status"] = "Paid"
            pay["transaction_reference"] = transaction_ref
            return {"success": True, "status": "Paid", "payment_id": payment_id}
        return {"success": False, "status": "NOT_FOUND", "payment_id": payment_id}

    def mark_payment_status(self, payment_id: str, new_status: str = "Paid", transaction_reference: str = "") -> dict:
        pay = self._payments_store.get(payment_id)
        if pay:
            pay["status"] = new_status
            if transaction_reference:
                pay["transaction_reference"] = transaction_reference
            return {"success": True, "status": new_status, "payment_id": payment_id}
        return {"success": False, "status": "NOT_FOUND", "payment_id": payment_id}

    def generate_offline_upi_qr(self, amount: str, clinic_name: str, reference: str, output_dir: Path) -> dict:
        try:
            numeric_amount = Decimal(str(amount).replace(",", "").replace("₹", "").strip())
            if numeric_amount <= 0:
                raise InvalidOperation
            upi_id = self._upi_id or "clinic@upi"
            uri = "upi://pay?" + urlencode({"pa": upi_id, "pn": clinic_name, "am": f"{numeric_amount:.2f}", "cu": "INR", "tr": reference})
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / f"{reference}-upi.png"
            qrcode.make(uri).save(path)
            return {"success": True, "upi_id": upi_id, "amount": float(numeric_amount), "qr_path": str(path), "upi_uri": uri}
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "error_code": "INVALID_AMOUNT", "message": "A valid consultation amount is required."}