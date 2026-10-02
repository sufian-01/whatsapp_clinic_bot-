"""Comprehensive test suite for CMS upgrades: concurrency, audit logging,

manual bookings, duplicate detection, doctor deactivation safety,
payment reconciliation, invoices, and formula injection sanitization.
"""

from concurrent.futures import ThreadPoolExecutor
import io
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.core.auth import create_session
from app.core.config import Settings
from app.main import create_app
from app.services.audit_service import AuditService
from app.services.crm_service import CrmService, sanitize_csv_field
from app.tools.appointments import AppointmentTools
from app.tools.doctors import DoctorDirectory, DoctorTools
from app.tools.invoice import InvoiceData, generate_invoice
from app.tools.invoices import InvoiceTools
from app.tools.patients import PatientRecord, PatientRepository, PatientTools
from app.tools.payments import PaymentTools
from app.tools.slots import SlotRepository


class MockStorage:
    def __init__(self):
        self.doctor_rows = [
            ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
            ["D1", "Dr. Arjun Mehta", "General Physician", "Monday, Wednesday, Friday", "10:00 AM", "1:00 PM", "500", "Active"],
            ["D2", "Dr. Sana Khan", "Gynecologist", "Tuesday, Thursday, Saturday", "11:00 AM", "2:00 PM", "700", "Active"],
        ]
        self.patient_rows = [
            [
                "Patient ID", "Name", "Email", "Phone", "Age", "Gender",
                "Doctor", "Appointment Date", "Appointment Time", "Token No",
                "Amount", "Payment Method", "Payment Status", "Booking Status", "Created At"
            ],
            [
                "PAT-001", "John Doe", "john@example.com", "9876543210", "30", "Male",
                "Dr. Arjun Mehta", "2026-10-15", "10:00 AM", "TKN-001",
                "500", "Offline", "Pending", "Confirmed", "2026-10-01T09:00:00Z"
            ],
            [
                "PAT-002", "Jane Smith", "jane@example.com", "9876543211", "28", "Female",
                "Dr. Sana Khan", "2026-10-16", "11:00 AM", "TKN-002",
                "700", "Offline", "Paid", "Confirmed", "2026-10-01T10:00:00Z"
            ],
            [
                "PAT-003", "=HYPERLINK('http://malicious.com','Click')", "+1234567890", "malicious@test.com", "40", "Other",
                "Dr. Arjun Mehta", "2026-10-17", "10:30 AM", "TKN-003",
                "-500", "@admin", "Paid", "Completed", "2026-10-01T11:00:00Z"
            ]
        ]
        self.slot_rows = [
            ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"],
            ["S1", "D1", "Dr. Arjun Mehta", "2026-10-15", "10:00 AM", "10:30 AM", "Booked", "PAT-001", "TKN-001", "2026-10-01T09:00:00Z"],
            ["S2", "D1", "Dr. Arjun Mehta", "2026-10-15", "10:30 AM", "11:00 AM", "Available", "", "", ""],
            ["S3", "D2", "Dr. Sana Khan", "2026-10-16", "11:00 AM", "11:30 AM", "Booked", "PAT-002", "TKN-002", "2026-10-01T10:00:00Z"],
            ["S4", "D2", "Dr. Sana Khan", "2026-10-16", "11:30 AM", "12:00 PM", "Available", "", "", ""],
        ]

    def read_doctors(self):
        return [row[:] for row in self.doctor_rows]

    def append_doctor(self, values, range_name):
        self.doctor_rows.append(list(values))
        return {"updatedRows": 1}

    def update_doctor(self, range_name, values):
        row_str = range_name.split("!")[1].split(":")[0][1:]
        row_idx = int(row_str) - 1
        for i, val in enumerate(values):
            if i < len(self.doctor_rows[row_idx]):
                self.doctor_rows[row_idx][i] = str(val)
        return {"updatedCells": len(values)}

    def read_patients(self):
        return [row[:] for row in self.patient_rows]

    def append_patient(self, values, range_name):
        self.patient_rows.append(list(values))
        return {"updatedRows": 1}

    def update_patient(self, range_name, values):
        cell_part = range_name.split("!")[1]
        if ":" in cell_part:
            row_str = cell_part.split(":")[0][1:]
            row_idx = int(row_str) - 1
            for i, val in enumerate(values):
                if i < len(self.patient_rows[row_idx]):
                    self.patient_rows[row_idx][i] = str(val)
        else:
            col_letter = cell_part[0]
            row_idx = int(cell_part[1:]) - 1
            col_idx = ord(col_letter) - ord('A')
            if col_idx < len(self.patient_rows[row_idx]):
                self.patient_rows[row_idx][col_idx] = str(values[0])
        return {"updatedCells": len(values)}

    def read_slots(self):
        return [row[:] for row in self.slot_rows]

    def append_slot(self, values, range_name):
        self.slot_rows.append(list(values))
        return {"updatedRows": 1}

    def update_slot(self, range_name, values):
        cell_part = range_name.split("!")[1]
        row_str = cell_part.split(":")[0][1:]
        row_idx = int(row_str) - 1
        for i, val in enumerate(values):
            if i < len(self.slot_rows[row_idx]):
                self.slot_rows[row_idx][i] = str(val)
        return {"updatedCells": len(values)}


class CmsUpgradesTests(unittest.TestCase):
    def setUp(self):
        self.storage = MockStorage()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_log_path = Path(self.temp_dir.name) / "test_audit.jsonl"
        self.audit = AuditService(log_file=self.audit_log_path)

        self.patient_repo = PatientRepository(
            self.storage.read_patients,
            self.storage.append_patient,
            self.storage.update_patient,
            "patient!A1:O1000",
        )
        self.patients = PatientTools(self.patient_repo)

        self.doctor_dir = DoctorDirectory(
            self.storage.read_doctors,
            append_row=self.storage.append_doctor,
            update_cells=self.storage.update_doctor,
            sheet_range="doctor!A1:H1000",
        )
        self.doctors = DoctorTools(self.doctor_dir)

        self.slot_repo = SlotRepository(
            self.storage.read_slots,
            self.storage.update_slot,
            "appointment_slots!A1:J5000",
            append_row=self.storage.append_slot,
        )
        self.slots = AppointmentTools(self.slot_repo)
        self.payments = PaymentTools()
        self.invoices = InvoiceTools()

        self.crm = CrmService(
            patients_tools=self.patients,
            doctors_tools=self.doctors,
            slots_tools=self.slots,
            payments_tools=self.payments,
            invoices_tools=self.invoices,
            audit_service=self.audit,
            clinic_name="Hope CMS Clinic",
            clinic_timezone="Asia/Kolkata",
        )

        from app.api.admin import create_admin_router
        from fastapi import FastAPI

        self.test_app = FastAPI()
        settings = Settings(
            clinic_name="Hope CMS Clinic",
            telegram_bot_token="",
            telegram_webhook_secret="",
            gemini_api_key="",
            gemini_model="gemini-2.0-flash",
            telegram_webhook_url="",
            knowledge_dir=Path(self.temp_dir.name),
            vectorstore_dir=Path(self.temp_dir.name),
            crm_admin_username="admin",
            crm_admin_password="password123",
        )
        self.test_app.include_router(create_admin_router(self.crm, settings))
        self.client = TestClient(self.test_app)
        self.token = create_session("admin", "admin")

    def tearDown(self):
        self.temp_dir.cleanup()

    # -----------------------------------------------------------------------
    # 1. Concurrency: Double Booking Prevention
    # -----------------------------------------------------------------------
    def test_concurrent_slot_booking_rejects_double_booking(self):
        """Two concurrent booking requests for the same available slot S2."""
        results = []

        def attempt_booking(name, phone):
            try:
                res = self.crm.create_appointment_manual({
                    "slot_id": "S2",
                    "name": name,
                    "phone": phone,
                    "amount": "500",
                })
                return ("SUCCESS", res)
            except Exception as e:
                return ("FAILED", str(e))

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(attempt_booking, "Alice Walker", "9876500001")
            f2 = executor.submit(attempt_booking, "Bob Taylor", "9876500002")
            results.append(f1.result())
            results.append(f2.result())

        statuses = [r[0] for r in results]
        # Exactly one must succeed, and one must fail
        self.assertEqual(statuses.count("SUCCESS"), 1)
        self.assertEqual(statuses.count("FAILED"), 1)

        # Slot S2 must now be Booked in storage
        slot_s2 = self.slot_repo.get_slot_by_id("S2")
        self.assertEqual(slot_s2["Status"], "Booked")

    # -----------------------------------------------------------------------
    # 2. Patient Duplicate Detection & Soft Deactivation
    # -----------------------------------------------------------------------
    def test_patient_duplicate_detection(self):
        # Existing phone in storage is 9876543210
        check = self.crm.check_patient_duplicates(phone="9876543210")
        self.assertTrue(check["has_duplicates"])
        self.assertEqual(len(check["duplicates"]), 1)
        self.assertEqual(check["duplicates"][0]["patient_id"], "PAT-001")

        # Non-existing phone
        check2 = self.crm.check_patient_duplicates(phone="9999999999")
        self.assertFalse(check2["has_duplicates"])

    def test_create_patient_with_dedup_flag(self):
        # Create with duplicate phone and force=False -> Rejected
        payload = {"name": "Duplicate John", "phone": "9876543210"}
        res = self.crm.create_patient_with_dedup(payload, force=False)
        self.assertFalse(res["success"])
        self.assertTrue(res["duplicate_detected"])

        # Create with force=True -> Succeeded
        res_forced = self.crm.create_patient_with_dedup(payload, force=True)
        self.assertTrue(res_forced["success"])

    def test_patient_soft_deactivation(self):
        res = self.crm.deactivate_patient("PAT-001")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "Inactive")

        # Verify audit log was recorded
        logs = self.audit.get_logs(action="PATIENT_DEACTIVATE")
        self.assertEqual(logs["total"], 1)
        self.assertEqual(logs["logs"][0]["entity_id"], "PAT-001")

    def test_patient_details_with_financial_balance(self):
        details = self.crm.get_patient("PAT-001")
        self.assertIsNotNone(details)
        self.assertEqual(details["patient_id"], "PAT-001")
        self.assertEqual(details["total_billed"], 500.0)
        self.assertEqual(details["total_paid"], 0.0)
        self.assertEqual(details["pending_balance"], 500.0)

    # -----------------------------------------------------------------------
    # 3. Doctor Deactivation Safety Verification
    # -----------------------------------------------------------------------
    def test_doctor_deactivation_safety_check(self):
        # D1 has an upcoming confirmed appointment on 2026-10-15
        safety = self.crm.check_doctor_deactivation_safety("D1", today_str="2026-10-01")
        self.assertFalse(safety["safe_to_deactivate"])
        self.assertEqual(safety["upcoming_appointments_count"], 1)

        # Non-existing doctor raises ValueError
        with self.assertRaises(ValueError):
            self.crm.check_doctor_deactivation_safety("NONEXISTENT")

    def test_doctor_status_toggle_records_audit_log(self):
        success = self.crm.set_doctor_status("D1", "Inactive")
        self.assertTrue(success)

        logs = self.audit.get_logs(action="DOCTOR_STATUS_CHANGE")
        self.assertEqual(logs["total"], 1)
        self.assertEqual(logs["logs"][0]["entity_id"], "D1")
        self.assertEqual(logs["logs"][0]["details"]["status"], "Inactive")

    # -----------------------------------------------------------------------
    # 4. Manual Payment Recording
    # -----------------------------------------------------------------------
    def test_record_manual_payment(self):
        res = self.crm.record_manual_payment(
            identifier="TKN-001",
            amount="500",
            payment_method="Cash",
            transaction_ref="RCPT-9876",
            notes="Collected at reception",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["payment_status"], "Paid")

        # Verify payment in CRM shows Paid
        pay = self.crm.get_payment("TKN-001")
        self.assertEqual(pay["payment_status"], "Paid")

        # Verify audit log
        logs = self.audit.get_logs(action="PAYMENT_RECORD")
        self.assertEqual(logs["total"], 1)
        self.assertEqual(logs["logs"][0]["entity_id"], "TKN-001")
        self.assertEqual(logs["logs"][0]["details"]["transaction_ref"], "RCPT-9876")

    # -----------------------------------------------------------------------
    # 5. PDF Invoice Generation
    # -----------------------------------------------------------------------
    def test_generate_appointment_invoice(self):
        inv = self.crm.generate_appointment_invoice("TKN-001")
        self.assertTrue(inv["success"])
        self.assertTrue(inv["invoice_number"].startswith("INV-"))
        pdf_file = Path(inv["file_path"])
        self.assertTrue(pdf_file.exists())
        self.assertGreater(pdf_file.stat().st_size, 100)

    def test_invoice_api_download(self):
        res = self.client.get(
            "/api/admin/appointments/TKN-001/invoice",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/pdf")
        self.assertIn("attachment", res.headers.get("content-disposition", ""))

    # -----------------------------------------------------------------------
    # 6. Formula Injection Neutralization in CSV Exports (CWE-1236)
    # -----------------------------------------------------------------------
    def test_csv_field_sanitization(self):
        self.assertEqual(sanitize_csv_field("=SUM(A1:A10)"), "'=SUM(A1:A10)")
        self.assertEqual(sanitize_csv_field("+1234"), "'+1234")
        self.assertEqual(sanitize_csv_field("-500"), "'-500")
        self.assertEqual(sanitize_csv_field("@dangerous"), "'@dangerous")
        self.assertEqual(sanitize_csv_field("Normal Text"), "Normal Text")

    def test_export_report_csv_with_sanitized_data(self):
        # Patient PAT-003 has malicious formula payload `=HYPERLINK(...)` and `@admin`
        csv_out = self.crm.export_report_csv("appointments")
        self.assertIn("'=HYPERLINK", csv_out)
        self.assertIn("'-500", csv_out)
        self.assertIn("'@admin", csv_out)

    def test_reports_export_api_endpoints(self):
        # Test appointments export
        res_appts = self.client.get(
            "/api/admin/reports/export?type=appointments",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(res_appts.status_code, 200)
        self.assertEqual(res_appts.headers["content-type"], "text/csv; charset=utf-8")

        # Test patients export
        res_patients = self.client.get(
            "/api/admin/reports/export?type=patients",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(res_patients.status_code, 200)

        # Test payments export
        res_payments = self.client.get(
            "/api/admin/reports/export?type=payments",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(res_payments.status_code, 200)

    # -----------------------------------------------------------------------
    # 7. Audit & Activity Logs API
    # -----------------------------------------------------------------------
    def test_audit_logs_query_and_api(self):
        # Trigger an action
        self.crm.update_appointment_status("TKN-001", "Completed", admin_user="admin")

        res = self.client.get(
            "/api/admin/audit-logs",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["logs"][0]["action"], "APPOINTMENT_STATUS_UPDATE")
        self.assertEqual(data["logs"][0]["entity_id"], "TKN-001")

    # -----------------------------------------------------------------------
    # 8. Extended Analytics Endpoint
    # -----------------------------------------------------------------------
    def test_dashboard_analytics_api(self):
        res = self.client.get(
            "/api/admin/dashboard/analytics?preset=this_month",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_appointments", data)
        self.assertIn("revenue_collected", data)
        self.assertIn("doctor_workload", data)


if __name__ == "__main__":
    unittest.main()
