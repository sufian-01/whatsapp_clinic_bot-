"""Comprehensive tests for Clinic CRM Admin Dashboard backend and frontend integration."""

import unittest
from fastapi.testclient import TestClient

from app.core.auth import _ACTIVE_SESSIONS, hash_password
from app.core.config import Settings
from app.main import create_app
from app.services.crm_service import CrmService
from app.tools.appointments import AppointmentTools
from app.tools.doctors import DoctorDirectory, DoctorTools
from app.tools.patients import PatientRecord, PatientRepository, PatientTools
from app.tools.payments import PaymentTools
from app.tools.slots import SlotRepository


class MockSheetStorage:
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
                "Dr. Arjun Mehta", "2026-09-30", "10:00 AM", "TKN-001",
                "500", "Offline", "Pending", "Confirmed", "2026-09-30T09:00:00Z"
            ],
            [
                "PAT-002", "Jane Smith", "jane@example.com", "9876543211", "28", "Female",
                "Dr. Sana Khan", "2026-10-01", "11:00 AM", "TKN-002",
                "700", "Offline", "Paid", "Confirmed", "2026-09-29T10:00:00Z"
            ],
        ]
        self.slot_rows = [
            ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"],
            ["S1", "D1", "Dr. Arjun Mehta", "2026-09-30", "10:00 AM", "10:30 AM", "Booked", "PAT-001", "TKN-001", "2026-09-30T09:00:00Z"],
            ["S2", "D1", "Dr. Arjun Mehta", "2026-09-30", "10:30 AM", "11:00 AM", "Available", "", "", ""],
            ["S3", "D2", "Dr. Sana Khan", "2026-10-01", "11:00 AM", "11:30 AM", "Booked", "PAT-002", "TKN-002", "2026-09-29T10:00:00Z"],
            ["S4", "D2", "Dr. Sana Khan", "2026-10-01", "11:30 AM", "12:00 PM", "Available", "", "", ""],
        ]

    def read_doctors(self):
        return [row[:] for row in self.doctor_rows]

    def append_doctor(self, values, range_name):
        self.doctor_rows.append(list(values))
        return {"updatedRows": 1}

    def update_doctor(self, range_name, values):
        # Range e.g. "doctor!A2:H2"
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


class AdminCrmTests(unittest.TestCase):
    def setUp(self):
        _ACTIVE_SESSIONS.clear()
        self.storage = MockSheetStorage()

        self.doc_dir = DoctorDirectory(
            read_rows=self.storage.read_doctors,
            append_row=self.storage.append_doctor,
            update_cells=self.storage.update_doctor,
            sheet_range="doctor!A1:H1000",
        )
        self.doc_tools = DoctorTools(self.doc_dir)

        self.patient_repo = PatientRepository(
            read_rows=self.storage.read_patients,
            append_row=self.storage.append_patient,
            update_cells=self.storage.update_patient,
            sheet_range="patient!A1:O1000",
        )
        self.patient_tools = PatientTools(self.patient_repo)

        self.slot_repo = SlotRepository(
            read_rows=self.storage.read_slots,
            update_cells=self.storage.update_slot,
            sheet_range="appointment_slots!A1:J1000",
            append_row=self.storage.append_slot,
        )
        self.slot_tools = AppointmentTools(self.slot_repo)
        self.pay_tools = PaymentTools()

        self.crm_service = CrmService(
            patients_tools=self.patient_tools,
            doctors_tools=self.doc_tools,
            slots_tools=self.slot_tools,
            payments_tools=self.pay_tools,
            clinic_name="Hope Clinic",
        )

        from fastapi import FastAPI
        from app.api.admin import create_admin_router
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import RedirectResponse
        from pathlib import Path

        self.settings = Settings(
            clinic_name="Hope Clinic",
            telegram_bot_token="fake_token",
            telegram_webhook_secret="fake_secret",
            gemini_api_key="fake_key",
            gemini_model="gemini-2.0-flash",
            telegram_webhook_url="https://example.com/webhook",
            knowledge_dir=Path("./data/knowledge"),
            vectorstore_dir=Path("./data/vectorstore"),
            crm_admin_username="admin",
            crm_admin_password="secretpassword",
        )

        self.app = FastAPI()
        self.app.include_router(create_admin_router(self.crm_service, self.settings))

        frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
        if frontend_dir.exists():
            @self.app.get("/admin", include_in_schema=False)
            async def admin_redirect():
                return RedirectResponse(url="/admin/")

            self.app.mount("/admin", StaticFiles(directory=str(frontend_dir), html=True), name="admin")

        @self.app.get("/health")
        async def health():
            return {"status": "ok"}

        self.client = TestClient(self.app)

    def _login(self):
        res = self.client.post("/api/admin/auth/login", json={"username": "admin", "password": "secretpassword"})
        self.assertEqual(res.status_code, 200)
        return res.json()["token"]

    # 1. Authentication Tests
    def test_auth_login_success(self):
        res = self.client.post("/api/admin/auth/login", json={"username": "admin", "password": "secretpassword"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("token", data)
        self.assertEqual(data["username"], "admin")
        self.assertEqual(data["role"], "admin")
        self.assertEqual(data["clinic_name"], "Hope Clinic")

    def test_auth_login_invalid_password(self):
        res = self.client.post("/api/admin/auth/login", json={"username": "admin", "password": "wrongpassword"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("Invalid username or password", res.json()["detail"])

    def test_auth_login_invalid_user(self):
        res = self.client.post("/api/admin/auth/login", json={"username": "nonexistent", "password": "secretpassword"})
        self.assertEqual(res.status_code, 401)

    def test_unauthorized_access_rejected(self):
        res = self.client.get("/api/admin/dashboard/stats")
        self.assertEqual(res.status_code, 401)

    def test_auth_me_endpoint(self):
        token = self._login()
        res = self.client.get("/api/admin/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["username"], "admin")
        self.assertEqual(res.json()["clinic_name"], "Hope Clinic")

    def test_auth_logout_revokes_token(self):
        token = self._login()
        res_me = self.client.get("/api/admin/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_me.status_code, 200)

        # Logout
        res_logout = self.client.post("/api/admin/auth/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_logout.status_code, 200)

        # Token should now be invalid
        res_after = self.client.get("/api/admin/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_after.status_code, 401)

    # 2. Dashboard Tests
    def test_dashboard_stats(self):
        token = self._login()
        res = self.client.get("/api/admin/dashboard/stats?today=2026-09-30", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_patients"], 2)
        self.assertEqual(data["total_doctors"], 2)
        self.assertEqual(data["active_doctors"], 2)
        self.assertEqual(data["today_appointments"], 1)
        self.assertEqual(data["upcoming_appointments"], 1)
        self.assertEqual(data["total_revenue"], 700.0)
        self.assertEqual(data["pending_payments"], 1)

    def test_dashboard_today_appointments(self):
        token = self._login()
        res = self.client.get("/api/admin/dashboard/today-appointments?today=2026-09-30", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["Token No"], "TKN-001")

    # 3. Patient Management Tests
    def test_patient_list_and_search(self):
        token = self._login()
        # All patients
        res = self.client.get("/api/admin/patients", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 2)

        # Search by phone
        res_search = self.client.get("/api/admin/patients?search=9876543210", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_search.status_code, 200)
        self.assertEqual(len(res_search.json()["patients"]), 1)
        self.assertEqual(res_search.json()["patients"][0]["name"], "John Doe")

    def test_patient_create(self):
        token = self._login()
        payload = {
            "name": "Alice Wonderland",
            "phone": "9998887776",
            "email": "alice@example.com",
            "age": "25",
            "gender": "Female",
        }
        res = self.client.post("/api/admin/patients", json=payload, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["success"])

        # Verify added to patient sheet
        res_list = self.client.get("/api/admin/patients?search=Alice", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(len(res_list.json()["patients"]), 1)

    def test_patient_update(self):
        token = self._login()
        res = self.client.put("/api/admin/patients/PAT-001", json={"email": "new_john@example.com", "age": "31"}, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)

        # Verify updated
        patient = self.client.get("/api/admin/patients/PAT-001", headers={"Authorization": f"Bearer {token}"}).json()
        self.assertEqual(patient["email"], "new_john@example.com")
        self.assertEqual(patient["age"], "31")

    # 4. Doctor Management Tests
    def test_doctor_list_and_create(self):
        token = self._login()
        res = self.client.get("/api/admin/doctors", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 2)

        # Create new doctor
        new_doc = {
            "name": "Dr. Rohit Verma",
            "specialization": "Dermatologist",
            "available_days": "Monday, Thursday",
            "start_time": "2:00 PM",
            "end_time": "5:00 PM",
            "consultation_fee": "600",
            "status": "Active",
        }
        res_create = self.client.post("/api/admin/doctors", json=new_doc, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_create.status_code, 201)

        # Verify doctor in list
        res_updated = self.client.get("/api/admin/doctors?search=Rohit", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(len(res_updated.json()), 1)

    def test_doctor_status_toggle(self):
        token = self._login()
        res = self.client.patch("/api/admin/doctors/D1/status", json={"status": "Inactive"}, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "Inactive")

        # Check active_only filter
        res_active = self.client.get("/api/admin/doctors?active_only=true", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(len(res_active.json()), 1)
        self.assertEqual(res_active.json()[0]["Doctor ID"], "D2")

    # 5. Appointment Management Tests
    def test_appointment_list_and_status_update(self):
        token = self._login()
        res = self.client.get("/api/admin/appointments", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total"], 2)

        # Update status Confirmed -> Completed
        res_update = self.client.patch("/api/admin/appointments/TKN-001/status", json={"status": "Completed"}, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(res_update.json()["status"], "Completed")

        # Completed is terminal; transition Completed -> Confirmed must fail
        res_invalid = self.client.patch("/api/admin/appointments/TKN-001/status", json={"status": "Confirmed"}, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_invalid.status_code, 400)

    # 6. Slot Management Tests & Safety Rules
    def test_slot_list_and_safety_rule(self):
        token = self._login()
        res = self.client.get("/api/admin/slots", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 4)

        # S1 is booked. Marking an actively booked slot Available must fail safety validation
        res_unsafe = self.client.patch("/api/admin/slots/S1/status", json={"status": "Available"}, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_unsafe.status_code, 400)
        self.assertIn("actively booked slot", res_unsafe.json()["detail"])

        # S2 is Available. Toggling to Unavailable is safe and should succeed
        res_safe = self.client.patch("/api/admin/slots/S2/status", json={"status": "Unavailable"}, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_safe.status_code, 200)

    # 7. Payment Management Tests
    def test_payment_list_and_mark_paid(self):
        token = self._login()
        res = self.client.get("/api/admin/payments?status=pending", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["payments"]), 1)
        self.assertEqual(res.json()["payments"][0]["token_no"], "TKN-001")

        # Mark as Paid
        res_pay = self.client.patch("/api/admin/payments/TKN-001/status", json={"status": "Paid"}, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_pay.status_code, 200)

        # Check now paid
        res_after = self.client.get("/api/admin/payments/TKN-001", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_after.json()["payment_status"], "Paid")

    # 8. Frontend Static Files Serving Tests
    def test_admin_frontend_served(self):
        # Redirect /admin -> /admin/
        res_redirect = self.client.get("/admin", follow_redirects=False)
        self.assertIn(res_redirect.status_code, (307, 308, 301, 302))

        # GET /admin/ serves index.html
        res_index = self.client.get("/admin/")
        self.assertEqual(res_index.status_code, 200)
        self.assertIn("Clinic CRM", res_index.text)
        self.assertIn("id=\"app-sidebar\"", res_index.text)

        # GET /admin/login.html serves login page
        res_login = self.client.get("/admin/login.html")
        self.assertEqual(res_login.status_code, 200)
        self.assertIn("Sign in to manage appointments", res_login.text)

        # GET static CSS & JS
        res_css = self.client.get("/admin/css/variables.css")
        self.assertEqual(res_css.status_code, 200)

        res_js = self.client.get("/admin/js/app.js")
        self.assertEqual(res_js.status_code, 200)


if __name__ == "__main__":
    unittest.main()
