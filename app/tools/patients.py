"""Explicit patient-sheet repository backed by the existing Sheets helpers."""

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
import time
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
    relationship_type: str = "Self"
    date_of_birth: str = ""


class PatientRepository:
    def __init__(
        self,
        read_rows: RowsReader,
        append_row: RowAppender,
        update_cells: CellUpdater,
        sheet_range: str,
        cache_ttl_seconds: float = 20.0,
    ) -> None:
        self._read_rows = read_rows
        self._append_row = append_row
        self._update_cells = update_cells
        self._sheet_range = sheet_range
        self._cache_ttl = cache_ttl_seconds
        self._cache_lock = RLock()
        self._cache_time: float = 0.0
        self._cached_rows: list[list[str]] | None = None
        self._cached_records: list[dict[str, str]] | None = None

    def invalidate_cache(self) -> None:
        """Invalidate the in-memory cache to force next read from sheet."""
        with self._cache_lock:
            self._cached_rows = None
            self._cached_records = None
            self._cache_time = 0.0

    def _rows(self, force_refresh: bool = False) -> list[list[str]]:
        with self._cache_lock:
            now = time.monotonic()
            if not force_refresh and self._cached_rows is not None and (now - self._cache_time) < self._cache_ttl:
                return [list(r) for r in self._cached_rows]
            try:
                rows = self._read_rows()
            except Exception:
                if self._cached_rows is not None:
                    return [list(r) for r in self._cached_rows]
                raise
            self._cached_rows = rows
            self._cached_records = None
            self._cache_time = now
            return [list(r) for r in rows]

    def _records(self, force_refresh: bool = False) -> list[dict[str, str]]:
        with self._cache_lock:
            now = time.monotonic()
            if not force_refresh and self._cached_records is not None and (now - self._cache_time) < self._cache_ttl:
                return [dict(r) for r in self._cached_records]
            rows = self._rows(force_refresh=force_refresh)
            if not rows:
                self._cached_records = []
                return []
            headers = [header.strip() for header in rows[0]]
            records = [
                {header: row[index].strip() if index < len(row) else "" for index, header in enumerate(headers)}
                for row in rows[1:]
                if any(cell.strip() for cell in row)
            ]
            self._cached_records = records
            return [dict(r) for r in records]

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
        self.invalidate_cache()
        return record

    def update_status(self, patient_id: str, status: str) -> bool:
        rows = self._rows(force_refresh=True)
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
                self.invalidate_cache()
                return True
        return False

    def list_records(self) -> list[dict[str, str]]:
        return self._records()

    def update_patient_details(self, patient_id: str, updates: dict[str, str]) -> bool:
        rows = self._rows(force_refresh=True)
        if not rows:
            return False
        headers = [h.strip() for h in rows[0]]
        if "Patient ID" not in headers:
            return False
        id_index = headers.index("Patient ID")

        # Map frontend / common keys to headers
        key_map = {
            "name": "Name",
            "email": "Email",
            "phone": "Phone",
            "age": "Age",
            "gender": "Gender",
            "doctor": "Doctor",
            "appointment_date": "Appointment Date",
            "appointment_time": "Appointment Time",
        }

        sheet_name = self._sheet_range.split("!", 1)[0]
        normalized_id = patient_id.strip()

        for row_number, row in enumerate(rows[1:], start=2):
            if id_index < len(row) and row[id_index].strip() == normalized_id:
                row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
                for k, v in updates.items():
                    target_header = key_map.get(k, k)
                    if target_header in headers:
                        row_dict[target_header] = str(v).strip()
                values = [row_dict.get(h, "") for h in headers]
                last_col = _column_name(len(headers) - 1)
                self._update_cells(f"{sheet_name}!A{row_number}:{last_col}{row_number}", values)
                self.invalidate_cache()
                return True
        return False

    def update_payment_status(self, identifier: str, payment_status: str) -> bool:
        rows = self._rows(force_refresh=True)
        if not rows:
            return False
        headers = [h.strip() for h in rows[0]]
        if "Payment Status" not in headers:
            return False
        pay_idx = headers.index("Payment Status")
        id_idx = headers.index("Patient ID") if "Patient ID" in headers else -1
        token_idx = headers.index("Token No") if "Token No" in headers else -1

        sheet_name = self._sheet_range.split("!", 1)[0]
        norm = identifier.strip()

        for row_number, row in enumerate(rows[1:], start=2):
            matches_id = id_idx >= 0 and id_idx < len(row) and row[id_idx].strip() == norm
            matches_token = token_idx >= 0 and token_idx < len(row) and row[token_idx].strip() == norm
            if matches_id or matches_token:
                self._update_cells(f"{sheet_name}!{_column_name(pay_idx)}{row_number}", [payment_status])
                self.invalidate_cache()
                return True
        return False

    def update_booking_status(self, identifier: str, booking_status: str) -> bool:
        rows = self._rows(force_refresh=True)
        if not rows:
            return False
        headers = [h.strip() for h in rows[0]]
        id_idx = headers.index("Patient ID") if "Patient ID" in headers else -1
        token_idx = headers.index("Token No") if "Token No" in headers else -1

        sheet_name = self._sheet_range.split("!", 1)[0]
        norm = identifier.strip()

        for row_number, row in enumerate(rows[1:], start=2):
            matches_id = id_idx >= 0 and id_idx < len(row) and row[id_idx].strip() == norm
            matches_token = token_idx >= 0 and token_idx < len(row) and row[token_idx].strip() == norm
            if matches_id or matches_token:
                if "Booking Status" in headers:
                    b_idx = headers.index("Booking Status")
                    self._update_cells(f"{sheet_name}!{_column_name(b_idx)}{row_number}", [booking_status])
                if "Status" in headers:
                    s_idx = headers.index("Status")
                    self._update_cells(f"{sheet_name}!{_column_name(s_idx)}{row_number}", [booking_status])
                self.invalidate_cache()
                return True
        return False

    def find_by_token(self, token_no: str) -> dict[str, str] | None:
        norm = token_no.strip().casefold()
        return next((r for r in self._records() if r.get("Token No", "").strip().casefold() == norm), None)

    def update_appointment_details(self, identifier: str, updates: dict[str, str]) -> bool:
        rows = self._rows(force_refresh=True)
        if not rows:
            return False
        headers = [h.strip() for h in rows[0]]
        id_idx = headers.index("Patient ID") if "Patient ID" in headers else -1
        token_idx = headers.index("Token No") if "Token No" in headers else -1

        key_map = {
            "name": "Name",
            "email": "Email",
            "phone": "Phone",
            "doctor": "Doctor",
            "appointment_date": "Appointment Date",
            "appointment_time": "Appointment Time",
            "amount": "Amount",
            "payment_method": "Payment Method",
            "payment_status": "Payment Status",
            "booking_status": "Booking Status",
            "status": "Booking Status",
        }

        sheet_name = self._sheet_range.split("!", 1)[0]
        norm = identifier.strip().casefold()

        for row_number, row in enumerate(rows[1:], start=2):
            matches_token = token_idx >= 0 and token_idx < len(row) and row[token_idx].strip().casefold() == norm
            matches_id = id_idx >= 0 and id_idx < len(row) and row[id_idx].strip().casefold() == norm
            if matches_token or matches_id:
                row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
                for k, v in updates.items():
                    target_h = key_map.get(k, k)
                    if target_h in headers:
                        row_dict[target_h] = str(v).strip()
                    if target_h == "Booking Status" and "Status" in headers:
                        row_dict["Status"] = str(v).strip()

                values = [row_dict.get(h, "") for h in headers]
                last_col = _column_name(len(headers) - 1)
                self._update_cells(f"{sheet_name}!A{row_number}:{last_col}{row_number}", values)
                self.invalidate_cache()
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

    def invalidate_cache(self) -> None:
        if hasattr(self._repository, "invalidate_cache"):
            self._repository.invalidate_cache()

    def list_patients(self) -> list[dict[str, str]]:
        return self._repository.list_records()

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

    def update_patient_details(self, patient_id: str, updates: dict[str, str]) -> dict:
        success = self._repository.update_patient_details(patient_id, updates)
        return {"success": success, "patient_id": patient_id}

    def update_payment_status(self, identifier: str, payment_status: str) -> dict:
        success = self._repository.update_payment_status(identifier, payment_status)
        return {"success": success, "identifier": identifier, "payment_status": payment_status}

    def update_booking_status(self, identifier: str, booking_status: str) -> dict:
        success = self._repository.update_booking_status(identifier, booking_status)
        return {"success": success, "identifier": identifier, "booking_status": booking_status}

    def find_by_token(self, token_no: str) -> dict | None:
        if not self._repository or not hasattr(self._repository, "find_by_token"):
            return None
        return self._repository.find_by_token(token_no)

    def update_appointment_details(self, identifier: str, updates: dict[str, str]) -> dict:
        if not self._repository or not hasattr(self._repository, "update_appointment_details"):
            return {"success": False, "error_code": "NOT_IMPLEMENTED"}
        success = self._repository.update_appointment_details(identifier, updates)
        return {"success": success, "identifier": identifier}



def _column_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name