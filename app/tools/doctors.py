"""Structured doctor lookups backed by a header-driven Google Sheet."""

from collections.abc import Callable
from typing import Protocol


class SheetReader(Protocol):
    def __call__(self) -> list[list[str]]: ...


class DoctorDirectory:
    def __init__(self, read_rows: SheetReader) -> None:
        self._read_rows = read_rows

    def get_doctors(self) -> list[dict[str, str]]:
        try:
            rows = self._read_rows()
        except Exception:
            return []
        if not rows:
            return []
        headers = [header.strip() for header in rows[0]]
        return [
            {header: row[index].strip() if index < len(row) else "" for index, header in enumerate(headers)}
            for row in rows[1:]
            if any(cell.strip() for cell in row)
        ]

    def get_doctor_by_name(self, name: str) -> list[dict[str, str]]:
        normalized = name.casefold().strip()
        return [
            doctor for doctor in self.get_doctors()
            if doctor.get("Doctor Name", "").casefold() == normalized
        ]

    def get_doctors_by_specialization(self, specialization: str) -> list[dict[str, str]]:
        normalized = specialization.casefold().strip()
        return [
            doctor for doctor in self.get_doctors()
            if normalized in doctor.get("Specialization", "").casefold()
        ]

    def get_doctor_schedule(self, name: str) -> list[dict[str, str]]:
        return [
            {
                key: doctor[key]
                for key in ("Doctor Name", "Available Days", "Start Time", "End Time", "Status")
                if doctor.get(key)
            }
            for doctor in self.get_doctor_by_name(name)
        ]


class DoctorTools:
    def __init__(self, directory: DoctorDirectory) -> None:
        self._directory = directory

    def get_doctors(self):
        return self._directory.get_doctors()

    def search_doctor(self, name: str):
        return self._directory.get_doctor_by_name(name)

    def get_doctors_by_specialization(self, specialization: str):
        return self._directory.get_doctors_by_specialization(specialization)

    def get_doctor_schedule(self, name: str):
        return self._directory.get_doctor_schedule(name)