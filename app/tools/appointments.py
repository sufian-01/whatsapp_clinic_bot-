"""Structured appointment-slot tools backed by SlotRepository."""


class AppointmentTools:
    def __init__(self, repository) -> None:
        self._repository = repository

    def list_all_slots(self) -> dict:
        try:
            slots = self._repository.list_all_slots()
            return {"success": True, "slots": slots}
        except Exception:
            return {"success": False, "slots": [], "error_code": "SLOT_READ_FAILED"}

    def get_available_slots(self, doctor: str, date: str) -> dict:
        try:
            slots = self._repository.get_available_slots(doctor, date)
            return {"success": True, "slots": slots}
        except Exception:
            return {"success": False, "slots": [], "error_code": "SLOT_READ_FAILED"}

    def get_upcoming_available_slots(self, doctor_name: str = "", doctor_id: str = "", from_date: str | None = None) -> dict:
        try:
            slots = self._repository.get_upcoming_available_slots(doctor_name, doctor_id, from_date)
            return {"success": True, "slots": slots}
        except Exception:
            return {"success": False, "slots": [], "error_code": "SLOT_READ_FAILED"}

    def get_slot(self, slot_id: str) -> dict:
        try:
            slot = self._repository.get_slot_by_id(slot_id)
            return {"success": bool(slot), "slot": slot, "error_code": None if slot else "SLOT_NOT_FOUND"}
        except Exception:
            return {"success": False, "slot": None, "error_code": "SLOT_READ_FAILED"}

    def get_slot_by_id(self, slot_id: str) -> dict | None:
        if not self._repository:
            return None
        return self._repository.get_slot_by_id(slot_id)

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

    def create_slot(self, data: dict) -> dict:
        try:
            slot = self._repository.create_slot(data)
            return {"success": True, "slot": slot}
        except Exception as error:
            return {"success": False, "error_code": "SLOT_CREATE_FAILED", "message": str(error)}

    def update_slot(self, slot_id: str, updates: dict) -> dict:
        try:
            slot = self._repository.update_slot(slot_id, updates)
            if not slot:
                return {"success": False, "error_code": "SLOT_NOT_FOUND"}
            return {"success": True, "slot": slot}
        except ValueError as err:
            return {"success": False, "error_code": "SLOT_SAFETY_VIOLATION", "message": str(err)}
        except Exception as err:
            return {"success": False, "error_code": "SLOT_UPDATE_FAILED", "message": str(err)}

    def set_slot_status(self, slot_id: str, status: str) -> dict:
        try:
            success = self._repository.set_slot_status(slot_id, status)
            return {"success": success, "slot_id": slot_id, "status": status}
        except ValueError as err:
            return {"success": False, "error_code": "SLOT_SAFETY_VIOLATION", "message": str(err)}
        except Exception as err:
            return {"success": False, "error_code": "SLOT_UPDATE_FAILED", "message": str(err)}

    def find_slot_by_booking(self, token_no: str | None = None, patient_id: str | None = None, doctor_name: str | None = None, date: str | None = None, start_time: str | None = None) -> dict | None:
        if not self._repository or not hasattr(self._repository, "find_slot_by_booking"):
            return None
        return self._repository.find_slot_by_booking(token_no=token_no, patient_id=patient_id, doctor_name=doctor_name, date=date, start_time=start_time)

    def release_slot_if_needed(self, slot_id: str, patient_id: str | None = None) -> bool:
        if not self._repository:
            return False
        return self._repository.release_slot_if_needed(slot_id, patient_id)
