import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.config import Settings
from app.tools.patients import PatientRecord, PatientRepository


HEADERS = [[
    "Patient ID", "Name", "Phone", "Age", "Gender", "Doctor",
    "Appointment Date", "Appointment Time", "Status", "Created At",
]]


class PatientTests(unittest.TestCase):
    def setUp(self):
        self.rows = HEADERS + [[
            "PAT-EXISTING", "Existing Patient", "+911234", "30", "", "",
            "", "", "Pending", "2026-09-25T00:00:00+00:00",
        ]]
        self.appended = []
        self.updated = []
        self.repository = PatientRepository(
            lambda: self.rows,
            lambda values, range_name: self.appended.append((values, range_name)),
            lambda range_name, values: self.updated.append((range_name, values)),
            "patient!A1:Z1000",
        )

    def test_create_patient_appends_to_patient_range(self):
        patient = self.repository.create_patient(PatientRecord(name="New Patient", phone="+919999"))
        self.assertTrue(patient.patient_id.startswith("PAT-"))
        self.assertEqual(self.appended[0][1], "patient!A1:Z1000")
        self.assertEqual(self.appended[0][0][1], "New Patient")

    def test_find_by_id_and_phone(self):
        self.assertEqual(self.repository.find_by_patient_id("PAT-EXISTING")["Name"], "Existing Patient")
        self.assertEqual(len(self.repository.find_by_phone("+911234")), 1)

    def test_update_status_uses_header_column(self):
        self.assertTrue(self.repository.update_status("PAT-EXISTING", "Confirmed"))
        self.assertEqual(self.updated, [("patient!I2", ["Confirmed"])])

    def test_duplicate_patient_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.repository.create_patient(PatientRecord(name="Duplicate", phone="+915555", patient_id="PAT-EXISTING"))
        self.assertEqual(self.appended, [])

    def test_generation_retries_a_collision(self):
        values = iter(["EXISTING", "UNIQUE000"])
        with patch("app.tools.patients.uuid4", side_effect=[type("UUID", (), {"hex": value})() for value in values]):
            patient = self.repository.create_patient(PatientRecord(name="Retry", phone="+916666"))
        self.assertEqual(patient.patient_id, "PAT-UNIQUE000")

    def test_sheet_failure_is_not_silently_converted_to_a_patient(self):
        failing = PatientRepository(
            lambda: (_ for _ in ()).throw(RuntimeError("sheet unavailable")),
            lambda values, range_name: None,
            lambda range_name, values: None,
            "patient!A1:Z1000",
        )
        with self.assertRaises(RuntimeError):
            failing.create_patient(PatientRecord(name="No Write", phone="+917777"))

    def test_missing_sheet_configuration_is_empty(self):
        settings = Settings(
            "Clinic", "token", "", "key", "model", "", Path("knowledge"), Path("vectorstore"),
            clinic_sheet_id="", patient_sheet_range="patient!A1:Z1000",
        )
        self.assertFalse(settings.clinic_sheet_id)
        self.assertEqual(settings.patient_sheet_range, "patient!A1:Z1000")