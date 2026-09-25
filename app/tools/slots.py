"""Google Sheets appointment-slot repository for the temporary booking phase."""

from datetime import datetime, timezone
from threading import RLock
from typing import Protocol


class SlotReader(Protocol):
    def __call__(self) -> list[list[str]]: ...


class SlotUpdater(Protocol):
    def __call__(self, range_name: str, values: list[str]) -> object: ...


class SlotRepository:
    _booking_lock = RLock()

    def __init__(self, read_rows: SlotReader, update_cells: SlotUpdater, sheet_range: str) -> None:
        self._read_rows = read_rows
        self._update_cells = update_cells
        self._sheet_range = sheet_range

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

    def get_available_slots(self, doctor: str, date: str) -> list[dict[str, str]]:
        _, records = self._snapshot()
        return [record for record in records if record.get("Doctor Name", "").casefold() == doctor.casefold() and record.get("Date") == date and record.get("Status", "").casefold() == "available"]

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


def _column_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name