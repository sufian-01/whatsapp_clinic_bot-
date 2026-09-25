"""Payment boundary; online payments intentionally remain unimplemented."""


class PaymentTools:
    def create_online_payment(self, amount: str) -> dict:
        return {"success": False, "status": "NOT_IMPLEMENTED", "message": "Online payment will be available soon."}

    def verify_payment_status(self, payment_id: str) -> dict:
        return {"success": False, "status": "NOT_IMPLEMENTED", "payment_id": payment_id}

    def record_offline_payment(self, amount: str) -> dict:
        return {"success": True, "payment_method": "Offline", "payment_status": "Pending", "amount": amount}

    def get_payment_status(self, payment_id: str) -> dict:
        return {"success": False, "status": "UNKNOWN", "payment_id": payment_id}