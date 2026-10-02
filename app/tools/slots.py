"""Google Sheets appointment-slot repository for the temporary booking phase."""

from datetime import date, datetime, timezone
from threading import RLock
from typing import Protocol


class SlotReader(Protocol):
    def __call__(self) -> list[list[str]]: ...


class SlotUpdater(Protocol):
    def __call__(self, range_name: str, values: list[str]) -> object: ...


class SlotAppender(Protocol):
    def __call__(self, values: list[str], range_name: str) -> object: ...


class SlotRepository:
    _booking_lock = RLock()

    def __init__(
        self,
        read_rows: SlotReader,
        update_cells: SlotUpdater,
        sheet_range: str,
        append_row: SlotAppender | None = None,
    ) -> None:
        self._read_rows = read_rows
        self._update_cells = update_cells
        self._sheet_range = sheet_range
        self._append_row = append_row

    def _snapshot(self) -> tuple[list[str], list[dict[str, str]]]:
        rows = self._read_rows()
        if not rows:
            return [], []
        headers = [value.strip() for value in rows[0]]
        records = []
        for row_number, row in enumerate(rows[1:], start=2):
            if any(cell.strip() for cell in row):
                records.append({
                    **{header: row[index].strip() if index < len(row) else "" for index, header in enumerate(headers)},
                    "_row_number": str(row_number),
                })
        return headers, records

    def list_all_slots(self) -> list[dict[str, str]]:
        """Return all slot records from the sheet."""
        _, records = self._snapshot()
        return records

    def get_available_slots(self, doctor: str, date: str) -> list[dict[str, str]]:
        _, records = self._snapshot()
        return [record for record in records if record.get("Doctor Name", "").casefold() == doctor.casefold() and record.get("Date") == date and record.get("Status", "").casefold() == "available"]

    def get_upcoming_available_slots(
        self,
        doctor_name: str = "",
        doctor_id: str = "",
        from_date: str | None = None,
    ) -> list[dict[str, str]]:
        """Return unique, well-formed, unbooked slots on or after ``from_date``."""
        _, records = self._snapshot()
        try:
            minimum = date.fromisoformat(from_date) if from_date else date.today()
        except ValueError:
            return []
        result: list[dict[str, str]] = []
        seen_slot_ids: set[str] = set()
        for record in records:
            if record.get("Status", "").casefold() != "available":
                continue
            if doctor_id:
                if record.get("Doctor ID", "") != doctor_id:
                    continue
            elif doctor_name and record.get("Doctor Name", "").casefold() != doctor_name.casefold():
                continue
            try:
                slot_date = date.fromisoformat(record.get("Date", ""))
            except ValueError:
                continue
            slot_id = record.get("Slot ID", "")
            if not slot_id or slot_id in seen_slot_ids or slot_date < minimum:
                continue
            seen_slot_ids.add(slot_id)
            result.append(record)
        return sorted(result, key=lambda item: (item.get("Date", ""), item.get("Start Time", ""), item.get("Slot ID", "")))

    def get_slot_by_id(self, slot_id: str) -> dict[str, str] | None:
        _, records = self._snapshot()
        return next((record for record in records if record.get("Slot ID") == slot_id), None)

    def get_booked_slots(self, doctor: str, date: str) -> list[dict[str, str]]:
        _, records = self._snapshot()
        return [record for record in records if record.get("Doctor Name", "").casefold() == doctor.casefold() and record.get("Date") == date and record.get("Status", "").casefold() == "booked"]

    def book_slot(self, slot_id: str, patient_id: str, token_no: str) -> bool:
        with self._booking_lock:
            headers, records = self._snapshot()
            slot = next((record for record in records if record.get("Slot ID") == slot_id), None)
            if not slot or slot.get("Status", "").casefold() != "available":
                return False
            slot["Status"] = "Booked"
            slot["Patient ID"] = patient_id
            slot["Token No"] = token_no
            slot["Booked At"] = datetime.now(timezone.utc).isoformat()
            row_number = slot.pop("_row_number")
            values = [slot.get(header, "") for header in headers]
            sheet_name = self._sheet_range.split("!", 1)[0]
            last_column = _column_name(len(headers) - 1)
            self._update_cells(f"{sheet_name}!A{row_number}:{last_column}{row_number}", values)
            verified = self.get_slot_by_id(slot_id)
            return bool(verified and verified.get("Status", "").casefold() == "booked" and verified.get("Patient ID") == patient_id)

    def release_slot_if_needed(self, slot_id: str, patient_id: str | None = None) -> bool:
        with self._booking_lock:
            headers, records = self._snapshot()
            slot = next((record for record in records if record.get("Slot ID") == slot_id), None)
            if not slot or slot.get("Status", "").casefold() != "booked" or (patient_id and slot.get("Patient ID") != patient_id):
                return False
            slot["Status"] = "Available"
            slot["Patient ID"] = ""
            slot["Token No"] = ""
            slot["Booked At"] = ""
            row_number = slot.pop("_row_number")
            values = [slot.get(header, "") for header in headers]
            sheet_name = self._sheet_range.split("!", 1)[0]
            self._update_cells(f"{sheet_name}!A{row_number}:{_column_name(len(headers) - 1)}{row_number}", values)
            return True

    def find_slot_by_booking(
        self,
        token_no: str | None = None,
        patient_id: str | None = None,
        doctor_name: str | None = None,
        date: str | None = None,
        start_time: str | None = None,
    ) -> dict[str, str] | None:
        """Find a booked slot matching token_no, patient_id, or doctor/date/time."""
        _, records = self._snapshot()
        if token_no:
            norm_tkn = token_no.strip().casefold()
            for r in records:
                if r.get("Token No", "").strip().casefold() == norm_tkn and r.get("Status", "").casefold() == "booked":
                    return r
        if patient_id:
            norm_pid = patient_id.strip().casefold()
            for r in records:
                if r.get("Patient ID", "").strip().casefold() == norm_pid and r.get("Status", "").casefold() == "booked":
                    return r
        if doctor_name and date and start_time:
            norm_doc = doctor_name.strip().casefold()
            for r in records:
                if (
                    r.get("Doctor Name", "").strip().casefold() == norm_doc
                    and r.get("Date", "").strip() == date.strip()
                    and r.get("Start Time", "").strip() == start_time.strip()
                    and r.get("Status", "").casefold() == "booked"
                ):
                    return r
        return None

    def create_slot(self, data: dict[str, str]) -> dict[str, str]:
        """Create a new slot record in the appointment_slots sheet."""
        if not self._append_row:
            raise RuntimeError("Slot appending is not configured")
        headers, records = self._snapshot()
        if not headers:
            headers = [
                "Slot ID", "Doctor ID", "Doctor Name", "Date",
                "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"
            ]

        slot_id = data.get("Slot ID") or data.get("slot_id") or ""
        if not slot_id:
            # Generate next slot ID
            max_num = 0
            for r in records:
                s_id = r.get("Slot ID", "")
                if s_id.startswith("S") and s_id[1:].isdigit():
                    max_num = max(max_num, int(s_id[1:]))
            slot_id = f"S{max_num + 1}"

        slot_record = {
            "Slot ID": slot_id,
            "Doctor ID": data.get("Doctor ID") or data.get("doctor_id", ""),
            "Doctor Name": data.get("Doctor Name") or data.get("doctor_name", ""),
            "Date": data.get("Date") or data.get("date", ""),
            "Start Time": data.get("Start Time") or data.get("start_time", ""),
            "End Time": data.get("End Time") or data.get("end_time", ""),
            "Status": data.get("Status") or data.get("status", "Available"),
            "Patient ID": data.get("Patient ID") or data.get("patient_id", ""),
            "Token No": data.get("Token No") or data.get("token_no", ""),
            "Booked At": data.get("Booked At") or data.get("booked_at", ""),
        }
        row_values = [slot_record.get(h, "") for h in headers]
        self._append_row(row_values, self._sheet_range)
        return slot_record

    def update_slot(self, slot_id: str, updates: dict[str, str]) -> dict[str, str] | None:
        """Update slot fields. Safety rule: cannot make booked slot available without validation."""
        headers, records = self._snapshot()
        slot = next((r for r in records if r.get("Slot ID") == slot_id), None)
        if not slot:
            return None

        # Check safety: if currently booked and new status is Available, prevent unless explicitly handled
        new_status = updates.get("Status") or updates.get("status")
        if slot.get("Status", "").casefold() == "booked" and new_status and new_status.casefold() == "available":
            # If still has patient ID and not released properly, reject unsafe modification
            if slot.get("Patient ID") and "force" not in updates:
                raise ValueError("Cannot mark an actively booked slot as available without releasing the patient appointment")

        key_map = {
            "doctor_id": "Doctor ID",
            "doctor_name": "Doctor Name",
            "date": "Date",
            "start_time": "Start Time",
            "end_time": "End Time",
            "status": "Status",
            "patient_id": "Patient ID",
            "token_no": "Token No",
        }
        for k, v in updates.items():
            h = key_map.get(k, k)
            if h in headers:
                slot[h] = str(v).strip()

        row_number = slot.pop("_row_number")
        values = [slot.get(header, "") for header in headers]
        sheet_name = self._sheet_range.split("!", 1)[0]
        self._update_cells(f"{sheet_name}!A{row_number}:{_column_name(len(headers) - 1)}{row_number}", values)
        return slot

    def set_slot_status(self, slot_id: str, status: str) -> bool:
        updated = self.update_slot(slot_id, {"Status": status})
        return updated is not None


def _column_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name
