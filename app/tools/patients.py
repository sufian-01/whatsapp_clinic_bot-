"""Explicit patient-sheet repository backed by the existing Sheets helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4


class RowsReader(Protocol):
    def __call__(self) -> list[list[str]]: ...


class RowAppender(Protocol):
    def __call__(self, values: list[str], range_name: str) -> object: ...


class CellUpdater(Protocol):
    def __call__(self, range_name: str, values: list[str]) -> object: ...


@dataclass(frozen=True)
class PatientRecord:
    name: str
    phone: str
    email: str = ""
    age: str = ""
    gender: str = ""
    doctor: str = ""
    appointment_date: str = ""
    appointment_time: str = ""
    status: str = "Pending"
    token_no: str = ""
    amount: str = ""
    payment_method: str = ""
    payment_status: str = "Pending"
    booking_status: str = "Pending"
    created_at: str = ""
    patient_id: str = ""


class PatientRepository:
    def __init__(self, read_rows: RowsReader, append_row: RowAppender, update_cells: CellUpdater, sheet_range: str) -> None:
        self._read_rows = read_rows
        self._append_row = append_row
        self._update_cells = update_cells
        self._sheet_range = sheet_range

    def _rows(self) -> list[list[str]]:
        return self._read_rows()

    def _records(self) -> list[dict[str, str]]:
        rows = self._rows()
        if not rows:
            return []
        headers = [header.strip() for header in rows[0]]
        return [
            {header: row[index].strip() if index < len(row) else "" for index, header in enumerate(headers)}
            for row in rows[1:]
            if any(cell.strip() for cell in row)
        ]

    def find_by_patient_id(self, patient_id: str) -> dict[str, str] | None:
        return next((record for record in self._records() if record.get("Patient ID") == patient_id), None)

    def find_by_phone(self, phone: str) -> list[dict[str, str]]:
        normalized = phone.strip()
        return [record for record in self._records() if record.get("Phone", "").strip() == normalized]

    def create_patient(self, patient: PatientRecord) -> PatientRecord:
        if not patient.name.strip() or not patient.phone.strip():
            raise ValueError("Patient name and phone are required")
        patient_id = patient.patient_id or self._new_patient_id()
        if self.find_by_patient_id(patient_id):
            raise ValueError("Patient ID already exists")
        created_at = patient.created_at or datetime.now(timezone.utc).isoformat()
        record = PatientRecord(**{**patient.__dict__, "patient_id": patient_id, "created_at": created_at})
        rows = self._rows()
        headers = [header.strip() for header in rows[0]] if rows else []
        required_headers = [
            "Patient ID", "Name", "Email", "Phone", "Age", "Gender", "Doctor",
            "Appointment Date", "Appointment Time", "Token No", "Amount",
            "Payment Method", "Payment Status", "Booking Status", "Created At",
        ]
        missing_headers = [header for header in required_headers if header not in headers]
        if missing_headers:
            headers = headers or ["Patient ID", "Name", "Phone", "Age", "Gender", "Doctor", "Appointment Date", "Appointment Time", "Status", "Created At"]
            headers.extend(missing_headers)
            self._update_cells(f"{self._sheet_range.split('!', 1)[0]}!A1:{_column_name(len(headers) - 1)}1", headers)
        values = {
            "Patient ID": record.patient_id,
            "Name": record.name,
            "Email": record.email,
            "Phone": record.phone,
            "Age": record.age,
            "Gender": record.gender,
            "Doctor": record.doctor,
            "Appointment Date": record.appointment_date,
            "Appointment Time": record.appointment_time,
            "Status": record.booking_status,
            "Token No": record.token_no,
            "Amount": record.amount,
            "Payment Method": record.payment_method,
            "Payment Status": record.payment_status,
            "Booking Status": record.booking_status,
            "Created At": record.created_at,
        }
        self._append_row([values.get(header, "") for header in headers], self._sheet_range)
        return record

    def update_status(self, patient_id: str, status: str) -> bool:
        rows = self._rows()
        if not rows:
            return False
        headers = [header.strip() for header in rows[0]]
        status_header = "Booking Status" if "Booking Status" in headers else "Status"
        if "Patient ID" not in headers or status_header not in headers:
            return False
        patient_index = headers.index("Patient ID")
        status_index = headers.index(status_header)
        for row_number, row in enumerate(rows[1:], start=2):
            if patient_index < len(row) and row[patient_index].strip() == patient_id:
                sheet_name = self._sheet_range.split("!", 1)[0]
                self._update_cells(f"{sheet_name}!{_column_name(status_index)}{row_number}", [status])
                return True
        return False

    def next_token(self) -> str:
        used = set()
        for record in self._records():
            value = record.get("Token No", "")
            if value.startswith("TKN-") and value[4:].isdigit():
                used.add(int(value[4:]))
        number = 1
        while number in used:
            number += 1
        return f"TKN-{number:04d}"

    def _new_patient_id(self) -> str:
        for _ in range(5):
            candidate = f"PAT-{uuid4().hex[:12].upper()}"
            if not self.find_by_patient_id(candidate):
                return candidate
        raise RuntimeError("Could not generate a unique patient ID")

    def new_patient_id(self) -> str:
        return self._new_patient_id()


class PatientTools:
    def __init__(self, repository: PatientRepository) -> None:
        self._repository = repository

    def generate_patient_id(self) -> dict:
        return {"success": True, "patient_id": self._repository.new_patient_id()}

    def generate_token(self) -> dict:
        return {"success": True, "token_no": self._repository.next_token()}

    def create_patient(self, patient: PatientRecord) -> dict:
        try:
            record = self._repository.create_patient(patient)
            return {"success": True, "patient": record}
        except Exception as error:
            return {"success": False, "error_code": "PATIENT_WRITE_FAILED", "message": str(error)}

    def find_patient_by_id(self, patient_id: str) -> dict:
        try:
            record = self._repository.find_by_patient_id(patient_id)
            return {"success": bool(record), "patient": record}
        except Exception:
            return {"success": False, "patient": None, "error_code": "PATIENT_READ_FAILED"}

    def find_patient_by_phone(self, phone: str) -> dict:
        try:
            records = self._repository.find_by_phone(phone)
            return {"success": True, "patients": records}
        except Exception:
            return {"success": False, "patients": [], "error_code": "PATIENT_READ_FAILED"}

    def update_patient(self, patient_id: str, status: str) -> dict:
        success = self._repository.update_status(patient_id, status)
        return {"success": success, "patient_id": patient_id, "status": status}


def _column_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name