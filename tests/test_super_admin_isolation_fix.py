"""Targeted tests for Super Admin & Tenant Isolation Fixes.

Verifies:
1. Super Admin login returns role="SUPER_ADMIN", clinic_name="Platform".
2. Super Admin calling /api/admin/auth/me returns clinic_name="Platform".
3. Super Admin without X-Tenant-ID resolves to tenant_id="platform", clinic_name="Platform" (never "default" or "XYZ Clinic").
4. Super Admin without X-Tenant-ID blocked from tenant-scoped clinical operations (HTTP 400).
5. Super Admin with X-Tenant-ID operates on specified tenant.
6. Tenant Admin cannot spoof or override assigned tenant via X-Tenant-ID (HTTP 403).
7. Inactive / Suspended tenant access denied (HTTP 403).
"""

import unittest
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.api.admin import create_admin_router
from app.core.auth import create_session, hash_password
from app.core.config import Settings
from app.core.tenant import (
    TenantContext,
    require_tenant,
    reset_tenant_status_cache,
    resolve_tenant_context,
    set_tenant_status,
)
from app.services.crm_service import CrmService
from app.tools.appointments import AppointmentTools
from app.tools.doctors import DoctorDirectory, DoctorTools
from app.tools.patients import PatientRepository, PatientTools
from app.tools.payments import PaymentTools
from app.tools.slots import SlotRepository


class MockStorage:
    def __init__(self):
        self.doctors = [
            ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
            ["D1", "Dr. A", "Cardiology", "Mon, Wed", "10:00 AM", "1:00 PM", "500", "Active"],
        ]
        self.patients = [
            ["Patient ID", "Name", "Email", "Phone", "Age", "Gender", "Doctor", "Appointment Date", "Appointment Time", "Token No", "Amount", "Payment Method", "Payment Status", "Booking Status", "Created At"],
        ]
        self.slots = [
            ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status", "Patient ID", "Token No", "Booked At"],
        ]

    def read_doctors(self): return [r[:] for r in self.doctors]
    def append_doctor(self, v, r): self.doctors.append(list(v)); return {"updatedRows": 1}
    def update_doctor(self, r, v): return {"updatedCells": len(v)}
    def read_patients(self): return [r[:] for r in self.patients]
    def append_patient(self, v, r): self.patients.append(list(v)); return {"updatedRows": 1}
    def update_patient(self, r, v): return {"updatedCells": len(v)}
    def read_slots(self): return [r[:] for r in self.slots]
    def append_slot(self, v, r): self.slots.append(list(v)); return {"updatedRows": 1}
    def update_slot(self, r, v): return {"updatedCells": len(v)}


class SuperAdminIsolationFixTests(unittest.TestCase):
    def setUp(self):
        reset_tenant_status_cache()
        self.storage = MockStorage()
        self.doc_tools = DoctorTools(DoctorDirectory(
            read_rows=self.storage.read_doctors,
            append_row=self.storage.append_doctor,
            update_cells=self.storage.update_doctor,
            sheet_range="doctor!A1:H1000",
        ))
        self.patient_tools = PatientTools(PatientRepository(
            read_rows=self.storage.read_patients,
            append_row=self.storage.append_patient,
            update_cells=self.storage.update_patient,
            sheet_range="patient!A1:O1000",
        ))
        self.slot_tools = AppointmentTools(SlotRepository(
            read_rows=self.storage.read_slots,
            update_cells=self.storage.update_slot,
            sheet_range="appointment_slots!A1:J1000",
            append_row=self.storage.append_slot,
        ))
        self.pay_tools = PaymentTools()
        self.crm_service = CrmService(
            patients_tools=self.patient_tools,
            doctors_tools=self.doc_tools,
            slots_tools=self.slot_tools,
            payments_tools=self.pay_tools,
            clinic_name="Default Clinic XYZ",
        )
        self.settings = Settings(
            clinic_name="Default Clinic XYZ",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="gem",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
            super_admin_username="superadmin",
            super_admin_password="SuperPassword123",
            crm_admin_username="admin",
            crm_admin_password="AdminPassword123",
        )
        self.app = FastAPI()
        self.app.include_router(create_admin_router(self.crm_service, self.settings))

        # Sample clinical endpoint requiring clinic tenant
        @self.app.get("/api/test-clinical-op")
        async def clinical_op(tenant: TenantContext = Depends(require_tenant)):
            return {
                "status": "ok",
                "tenant_id": tenant.tenant_id,
                "clinic_name": tenant.clinic_name,
            }

        # Sample resolution endpoint
        @self.app.get("/api/test-tenant-context")
        async def context_op(tenant: TenantContext = Depends(resolve_tenant_context)):
            return {
                "tenant_id": tenant.tenant_id,
                "clinic_name": tenant.clinic_name,
            }

        self.client = TestClient(self.app)

        self.super_token = create_session("superadmin", role="SUPER_ADMIN", tenant_id="platform")
        self.tenant_admin_token = create_session("clinic_admin_b", role="TENANT_ADMIN", tenant_id="clinic_b")

    def tearDown(self):
        reset_tenant_status_cache()

    def test_super_admin_login_response_has_platform_clinic_name(self):
        res = self.client.post(
            "/api/admin/auth/login",
            json={"username": "superadmin", "password": "SuperPassword123"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["role"], "SUPER_ADMIN")
        self.assertEqual(data["clinic_name"], "Platform")
        self.assertNotEqual(data["clinic_name"], "Default Clinic XYZ")

    def test_super_admin_auth_me_returns_platform_scope(self):
        res = self.client.get(
            "/api/admin/auth/me",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["role"], "SUPER_ADMIN")
        self.assertEqual(data["clinic_name"], "Platform")
        self.assertNotEqual(data["clinic_name"], "Default Clinic XYZ")

    def test_super_admin_resolves_to_platform_without_inheriting_default(self):
        res = self.client.get(
            "/api/test-tenant-context",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["tenant_id"], "platform")
        self.assertEqual(data["clinic_name"], "Platform")
        self.assertNotEqual(data["tenant_id"], "default")

    def test_super_admin_blocked_from_clinical_op_without_explicit_tenant(self):
        res = self.client.get(
            "/api/test-clinical-op",
            headers={"Authorization": f"Bearer {self.super_token}"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("explicit clinic tenant context", res.json()["detail"])

    def test_super_admin_can_operate_on_explicit_tenant(self):
        res = self.client.get(
            "/api/test-clinical-op",
            headers={
                "Authorization": f"Bearer {self.super_token}",
                "X-Tenant-ID": "clinic_charlie",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["tenant_id"], "clinic_charlie")
        self.assertEqual(data["clinic_name"], "Tenant clinic_charlie")

    def test_tenant_admin_cannot_spoof_different_tenant(self):
        res = self.client.get(
            "/api/test-clinical-op",
            headers={
                "Authorization": f"Bearer {self.tenant_admin_token}",
                "X-Tenant-ID": "clinic_another",
            },
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("You cannot access resources outside your assigned clinic tenant", res.json()["detail"])

    def test_tenant_admin_resolves_own_tenant_cleanly(self):
        res = self.client.get(
            "/api/test-clinical-op",
            headers={"Authorization": f"Bearer {self.tenant_admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["tenant_id"], "clinic_b")

    def test_inactive_tenant_denied(self):
        set_tenant_status("clinic_b", "INACTIVE")
        res = self.client.get(
            "/api/test-clinical-op",
            headers={"Authorization": f"Bearer {self.tenant_admin_token}"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("inactive", res.json()["detail"])

