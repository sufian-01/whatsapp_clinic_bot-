"""Structured appointment-slot tools backed by SlotRepository."""


class AppointmentTools:
    def __init__(self, repository) -> None:
        self._repository = repository

    def get_available_slots(self, doctor: str, date: str) -> dict:
        try:
            slots = self._repository.get_available_slots(doctor, date)
            return {"success": True, "slots": slots}
        except Exception:
            return {"success": False, "slots": [], "error_code": "SLOT_READ_FAILED"}

    def get_slot(self, slot_id: str) -> dict:
        try:
            slot = self._repository.get_slot_by_id(slot_id)
            return {"success": bool(slot), "slot": slot, "error_code": None if slot else "SLOT_NOT_FOUND"}
        except Exception:
            return {"success": False, "slot": None, "error_code": "SLOT_READ_FAILED"}

    def book_slot(self, slot_id: str, patient_id: str, token_no: str) -> dict:
        if not token_no:
            return {"success": False, "error_code": "TOKEN_REQUIRED", "message": "A token is required before booking."}
        try:
            success = self._repository.book_slot(slot_id, patient_id, token_no)
            return {"success": success, "slot_id": slot_id, "status": "booked" if success else "available", "patient_id": patient_id, "token_no": token_no, "error_code": None if success else "SLOT_ALREADY_BOOKED"}
        except Exception:
            return {"success": False, "slot_id": slot_id, "error_code": "SLOT_WRITE_FAILED"}

    def release_slot(self, slot_id: str, patient_id: str | None = None) -> dict:
        try:
            success = self._repository.release_slot_if_needed(slot_id, patient_id)
            return {"success": success, "slot_id": slot_id, "status": "available" if success else "unchanged"}
        except Exception:
            return {"success": False, "slot_id": slot_id, "error_code": "SLOT_RELEASE_FAILED"}