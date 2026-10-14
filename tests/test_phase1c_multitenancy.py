"""Tests for Phase 1C Multi-Tenant Foundation.

Verifies:
1. Cross-tenant data isolation for Patients, Doctors, Appointments, Slots,
   Prescriptions, Invoices, Payments, and Audit Logs.
2. Tenant A cannot read, query, or access Tenant B records.
3. Tenant-scoped cache key isolation and partition.
4. Tenant context enforcement (cannot be silently omitted).
5. Client-supplied X-Tenant-ID cannot override authenticated user tenant identity.
6. Multi-tenant slot and appointment concurrency uniqueness.
7. RAG knowledge isolation per tenant.
8. Storage path isolation and directory traversal prevention.
"""

from pathlib import Path
import tempfile
import unittest

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.auth import create_session
from app.core.cache import TenantCache, build_tenant_cache_key
from app.core.storage import (
    get_tenant_storage_path,
    get_tenant_storage_root,
    sanitize_filename,
    validate_tenant_file_access,
)
from app.core.tenant import (
    TenantContext,
    get_current_tenant,
    require_current_tenant,
    resolve_tenant_context,
    tenant_scope,
)
from app.db import (
    Appointment,
    AppointmentSlot,
    AuditLog,
    Base,
    Clinic,
    Doctor,
    Invoice,
    Patient,
    Payment,
    Prescription,
    PrescriptionItem,
    User,
)
from app.rag.tenant_service import TenantRagRegistry, TenantRagService
from app.repositories import (
    TenantAppointmentRepository,
    TenantAuditRepository,
    TenantDoctorRepository,
    TenantInvoiceRepository,
    TenantPatientRepository,
    TenantPaymentRepository,
    TenantPrescriptionRepository,
    TenantSlotRepository,
)


class DummyRequest:
    """Mock FastAPI Request for tenant resolution testing."""

    def __init__(self, headers=None, cookies=None):
        self.headers = headers or {}
        self.cookies = cookies or {}


class Phase1cMultitenancyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        # Create two distinct test clinics
        self.clinic_a = Clinic(
            id="tenant_clinic_a",
            name="Clinic Alpha",
            timezone="Asia/Kolkata",
            status="ACTIVE",
        )
        self.clinic_b = Clinic(
            id="tenant_clinic_b",
            name="Clinic Beta",
            timezone="Asia/Kolkata",
            status="ACTIVE",
        )
        self.session.add_all([self.clinic_a, self.clinic_b])
        self.session.commit()

        self.repo_patient_a = TenantPatientRepository(self.session, self.clinic_a.id)
        self.repo_patient_b = TenantPatientRepository(self.session, self.clinic_b.id)
        self.repo_doctor_a = TenantDoctorRepository(self.session, self.clinic_a.id)
        self.repo_doctor_b = TenantDoctorRepository(self.session, self.clinic_b.id)
        self.repo_slot_a = TenantSlotRepository(self.session, self.clinic_a.id)
        self.repo_slot_b = TenantSlotRepository(self.session, self.clinic_b.id)
        self.repo_appt_a = TenantAppointmentRepository(self.session, self.clinic_a.id)
        self.repo_appt_b = TenantAppointmentRepository(self.session, self.clinic_b.id)
        self.repo_rx_a = TenantPrescriptionRepository(self.session, self.clinic_a.id)
        self.repo_rx_b = TenantPrescriptionRepository(self.session, self.clinic_b.id)
        self.repo_inv_a = TenantInvoiceRepository(self.session, self.clinic_a.id)
        self.repo_inv_b = TenantInvoiceRepository(self.session, self.clinic_b.id)
        self.repo_pay_a = TenantPaymentRepository(self.session, self.clinic_a.id)
        self.repo_pay_b = TenantPaymentRepository(self.session, self.clinic_b.id)
        self.repo_audit_a = TenantAuditRepository(self.session, self.clinic_a.id)
        self.repo_audit_b = TenantAuditRepository(self.session, self.clinic_b.id)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    # -------------------------------------------------------------------------
    # 1. Tenant Isolation: Patients
    # -------------------------------------------------------------------------
    def test_patient_cross_tenant_isolation(self):
        # Create Patient A and Patient B
        p_a = self.repo_patient_a.create(name="Alice Alpha", phone="1111111111", patient_id="PAT-A")
        p_b = self.repo_patient_b.create(name="Bob Beta", phone="2222222222", patient_id="PAT-B")
        self.session.commit()

        # Tenant A can access its own patient
        self.assertIsNotNone(self.repo_patient_a.get("PAT-A"))
        self.assertEqual(self.repo_patient_a.get("PAT-A").name, "Alice Alpha")

        # Tenant A CANNOT retrieve Tenant B's patient
        self.assertIsNone(self.repo_patient_a.get("PAT-B"))
        self.assertEqual(len(self.repo_patient_a.get_by_phone("2222222222")), 0)

        # Tenant B CANNOT retrieve Tenant A's patient
        self.assertIsNone(self.repo_patient_b.get("PAT-A"))
        self.assertEqual(len(self.repo_patient_b.get_by_phone("1111111111")), 0)

        # List operation is strictly partitioned
        list_a = self.repo_patient_a.list()
        self.assertTrue(any(p.patient_id == "PAT-A" for p in list_a))
        self.assertFalse(any(p.patient_id == "PAT-B" for p in list_a))

    # -------------------------------------------------------------------------
    # 2. Tenant Isolation: Doctors
    # -------------------------------------------------------------------------
    def test_doctor_cross_tenant_isolation(self):
        d_a = self.repo_doctor_a.create(name="Dr. Alpha", specialization="Cardiology", doctor_id="DOC-A")
        d_b = self.repo_doctor_b.create(name="Dr. Beta", specialization="Dermatology", doctor_id="DOC-B")
        self.session.commit()

        # Tenant A retrieves own doctor
        self.assertIsNotNone(self.repo_doctor_a.get("DOC-A"))

        # Tenant A CANNOT retrieve Tenant B's doctor
        self.assertIsNone(self.repo_doctor_a.get("DOC-B"))
        self.assertIsNone(self.repo_doctor_b.get("DOC-A"))

        # Active list is strictly partitioned
        docs_a = [d.doctor_id for d in self.repo_doctor_a.list_active()]
        self.assertIn("DOC-A", docs_a)
        self.assertNotIn("DOC-B", docs_a)

    # -------------------------------------------------------------------------
    # 3. Tenant Isolation: Appointments
    # -------------------------------------------------------------------------
    def test_appointment_cross_tenant_isolation(self):
        p_a = self.repo_patient_a.create(name="P A", phone="100", patient_id="PAT-APPT-A")
        p_b = self.repo_patient_b.create(name="P B", phone="200", patient_id="PAT-APPT-B")
        d_a = self.repo_doctor_a.create(name="Doc A", specialization="GP", doctor_id="DOC-APPT-A")
        d_b = self.repo_doctor_b.create(name="Doc B", specialization="GP", doctor_id="DOC-APPT-B")
        self.session.commit()

        appt_a = self.repo_appt_a.create(
            patient_id=p_a.id,
            doctor_id=d_a.id,
            appointment_date="2026-10-30",
            appointment_time="10:00",
            token_no="TKN-A1",
        )
        appt_b = self.repo_appt_b.create(
            patient_id=p_b.id,
            doctor_id=d_b.id,
            appointment_date="2026-10-30",
            appointment_time="10:00",
            token_no="TKN-B1",
        )
        self.session.commit()

        # Tenant A sees own appointment
        self.assertIsNotNone(self.repo_appt_a.get("TKN-A1"))

        # Tenant A CANNOT retrieve Tenant B's appointment
        self.assertIsNone(self.repo_appt_a.get("TKN-B1"))
        self.assertIsNone(self.repo_appt_b.get("TKN-A1"))

        # Doctor appointments list is isolated
        appts_doc_a = self.repo_appt_a.list_by_doctor_and_date(d_a.id, "2026-10-30")
        self.assertEqual(len(appts_doc_a), 1)
        self.assertEqual(appts_doc_a[0].token_no, "TKN-A1")

    # -------------------------------------------------------------------------
    # 4. Tenant Isolation: Prescriptions
    # -------------------------------------------------------------------------
    def test_prescription_cross_tenant_isolation(self):
        p_a = self.repo_patient_a.create(name="P A", phone="101", patient_id="PAT-RX-A")
        d_a = self.repo_doctor_a.create(name="Doc A", specialization="GP", doctor_id="DOC-RX-A")
        p_b = self.repo_patient_b.create(name="P B", phone="201", patient_id="PAT-RX-B")
        d_b = self.repo_doctor_b.create(name="Doc B", specialization="GP", doctor_id="DOC-RX-B")
        self.session.commit()

        rx_a = self.repo_rx_a.create(
            patient_id=p_a.id,
            doctor_id=d_a.id,
            date="2026-10-30",
            diagnosis="Fever",
            prescription_id="RX-A1",
            medicines=[{"name": "Paracetamol", "dosage": "500mg"}],
        )
        rx_b = self.repo_rx_b.create(
            patient_id=p_b.id,
            doctor_id=d_b.id,
            date="2026-10-30",
            diagnosis="Cough",
            prescription_id="RX-B1",
            medicines=[{"name": "Syrup", "dosage": "10ml"}],
        )
        self.session.commit()

        self.assertIsNotNone(self.repo_rx_a.get("RX-A1"))
        self.assertIsNone(self.repo_rx_a.get("RX-B1"))
        self.assertIsNone(self.repo_rx_b.get("RX-A1"))

        # Query by patient_id is scoped to tenant
        self.assertEqual(len(self.repo_rx_a.list_by_patient(p_b.id)), 0)

    # -------------------------------------------------------------------------
    # 5. Tenant Isolation: Invoices & Payments
    # -------------------------------------------------------------------------
    def test_invoice_and_payment_cross_tenant_isolation(self):
        p_a = self.repo_patient_a.create(name="P A", phone="102", patient_id="PAT-INV-A")
        p_b = self.repo_patient_b.create(name="P B", phone="202", patient_id="PAT-INV-B")
        self.session.commit()

        inv_a = self.repo_inv_a.create(patient_id=p_a.id, amount="500", invoice_number="INV-A1")
        inv_b = self.repo_inv_b.create(patient_id=p_b.id, amount="700", invoice_number="INV-B1")
        pay_a = self.repo_pay_a.create(amount="500", payment_id="PAY-A1", invoice_id=inv_a.id)
        pay_b = self.repo_pay_b.create(amount="700", payment_id="PAY-B1", invoice_id=inv_b.id)
        self.session.commit()

        self.assertIsNotNone(self.repo_inv_a.get("INV-A1"))
        self.assertIsNone(self.repo_inv_a.get("INV-B1"))
        self.assertIsNotNone(self.repo_pay_a.get("PAY-A1"))
        self.assertIsNone(self.repo_pay_a.get("PAY-B1"))

    # -------------------------------------------------------------------------
    # 6. Tenant Isolation: Audit Logs
    # -------------------------------------------------------------------------
    def test_audit_log_cross_tenant_isolation(self):
        self.repo_audit_a.record(user="admin_a", action="CREATE_PATIENT", entity_type="patient", entity_id="PAT-A")
        self.repo_audit_b.record(user="admin_b", action="CREATE_DOCTOR", entity_type="doctor", entity_id="DOC-B")
        self.session.commit()

        logs_a = self.repo_audit_a.list()
        actions_a = [entry.action for entry in logs_a]
        self.assertIn("CREATE_PATIENT", actions_a)
        self.assertNotIn("CREATE_DOCTOR", actions_a)

        logs_b = self.repo_audit_b.list()
        actions_b = [entry.action for entry in logs_b]
        self.assertIn("CREATE_DOCTOR", actions_b)
        self.assertNotIn("CREATE_PATIENT", actions_b)

    # -------------------------------------------------------------------------
    # 7. Cache Key Isolation
    # -------------------------------------------------------------------------
    def test_tenant_cache_keys_cannot_collide(self):
        cache = TenantCache(default_ttl=30.0)

        # Store identical resource and arguments for two tenants
        key_a = cache.set("tenant_a", "doctors", ["Dr. Alpha"], "cardiology")
        key_b = cache.set("tenant_b", "doctors", ["Dr. Beta"], "cardiology")

        self.assertNotEqual(key_a, key_b)
        self.assertEqual(cache.get("tenant_a", "doctors", "cardiology"), ["Dr. Alpha"])
        self.assertEqual(cache.get("tenant_b", "doctors", "cardiology"), ["Dr. Beta"])

        # Invalidate Tenant A only
        cache.invalidate_tenant("tenant_a")
        self.assertIsNone(cache.get("tenant_a", "doctors", "cardiology"))
        self.assertEqual(cache.get("tenant_b", "doctors", "cardiology"), ["Dr. Beta"])

    # -------------------------------------------------------------------------
    # 8. Tenant Context & Missing Context Enforcement
    # -------------------------------------------------------------------------
    def test_tenant_context_enforcement(self):
        # Outside tenant_scope, require_current_tenant raises RuntimeError
        with self.assertRaises(RuntimeError) as ctx:
            require_current_tenant()
        self.assertIn("Tenant context is required", str(ctx.exception))

        # Inside tenant_scope, active tenant is available
        with tenant_scope("clinic_test_42") as t_ctx:
            self.assertEqual(t_ctx.tenant_id, "clinic_test_42")
            active = require_current_tenant()
            self.assertEqual(active.tenant_id, "clinic_test_42")

        # After exiting scope, tenant context is cleaned up
        self.assertIsNone(get_current_tenant())

        # Instantiating a repository without tenant_id raises ValueError
        with self.assertRaises(ValueError):
            TenantPatientRepository(self.session, "")

    # -------------------------------------------------------------------------
    # 9. Client-Supplied Tenant Header vs Authenticated Context
    # -------------------------------------------------------------------------
    def test_client_supplied_header_cannot_override_authenticated_tenant(self):
        import asyncio

        # User is authenticated with tenant 'tenant_alpha'
        session_token = create_session(username="admin_user", role="admin", tenant_id="tenant_alpha")

        # Client attempts to supply conflicting X-Tenant-ID header 'tenant_beta'
        req_spoofed = DummyRequest(
            headers={"Authorization": f"Bearer {session_token}", "X-Tenant-ID": "tenant_beta"}
        )

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(resolve_tenant_context(req_spoofed, x_tenant_id="tenant_beta"))
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access forbidden", ctx.exception.detail)

        # Matching header is permitted
        req_legit = DummyRequest(
            headers={"Authorization": f"Bearer {session_token}", "X-Tenant-ID": "tenant_alpha"}
        )
        resolved = asyncio.run(resolve_tenant_context(req_legit, x_tenant_id="tenant_alpha"))
        self.assertEqual(resolved.tenant_id, "tenant_alpha")

    # -------------------------------------------------------------------------
    # 10. Multi-Tenant Concurrency: Slots and Appointments
    # -------------------------------------------------------------------------
    def test_concurrency_uniqueness_is_tenant_scoped(self):
        # Two doctors with the same local identifier in two different clinics
        d_a = self.repo_doctor_a.create(name="Doc Local", specialization="GP", doctor_id="DOC-1")
        d_b = self.repo_doctor_b.create(name="Doc Local", specialization="GP", doctor_id="DOC-1")
        self.session.commit()

        # Slot at 10:00 for Tenant A
        s_a = self.repo_slot_a.create(
            doctor_id=d_a.id,
            date="2026-11-01",
            start_time="10:00",
            end_time="10:30",
            slot_id="SLT-A10",
        )
        self.session.commit()

        # Same slot at 10:00 for Tenant B SUCCEEDS independently (tenant-scoped constraint)
        s_b = self.repo_slot_b.create(
            doctor_id=d_b.id,
            date="2026-11-01",
            start_time="10:00",
            end_time="10:30",
            slot_id="SLT-B10",
        )
        self.session.commit()

        # But duplicate slot within the SAME tenant FAILS
        with self.assertRaises(IntegrityError):
            self.repo_slot_a.create(
                doctor_id=d_a.id,
                date="2026-11-01",
                start_time="10:00",
                end_time="10:30",
                slot_id="SLT-A10-DUP",
            )
            self.session.commit()
        self.session.rollback()

    # -------------------------------------------------------------------------
    # 11. RAG Tenant Knowledge Isolation
    # -------------------------------------------------------------------------
    def test_tenant_rag_isolation(self):
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            registry = TenantRagRegistry(base_dir=root)

            service_a = registry.get_service("clinic_a")
            service_b = registry.get_service("clinic_b")

            # Directories must be completely disjoint
            self.assertNotEqual(service_a.knowledge_dir, service_b.knowledge_dir)
            self.assertIn("clinic_a", str(service_a.knowledge_dir))
            self.assertIn("clinic_b", str(service_b.knowledge_dir))

            # Ingest doc in Clinic A
            doc_a = service_a.knowledge_dir / "clinic_a_policy.txt"
            doc_a.write_text("Clinic Alpha cardiology consultation fee is 800 rupees.", encoding="utf-8")

            # Ingest doc in Clinic B
            doc_b = service_b.knowledge_dir / "clinic_b_policy.txt"
            doc_b.write_text("Clinic Beta dental package is 1500 rupees.", encoding="utf-8")

            # File verification: Clinic A knowledge dir does not contain Clinic B doc
            self.assertTrue(doc_a.exists())
            self.assertTrue(doc_b.exists())
            self.assertFalse((service_a.knowledge_dir / "clinic_b_policy.txt").exists())
            self.assertFalse((service_b.knowledge_dir / "clinic_a_policy.txt").exists())

    # -------------------------------------------------------------------------
    # 12. Storage Path Partitioning and Traversal Prevention
    # -------------------------------------------------------------------------
    def test_tenant_storage_partitioning_and_security(self):
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)

            p_a = get_tenant_storage_path("tenant_1", "prescriptions", "RX-01.pdf", base_dir=root)
            p_b = get_tenant_storage_path("tenant_2", "prescriptions", "RX-01.pdf", base_dir=root)

            # Different tenants have isolated paths
            self.assertNotEqual(p_a, p_b)
            self.assertIn("tenant_1", str(p_a))
            self.assertIn("tenant_2", str(p_b))

            # Access validation
            self.assertTrue(validate_tenant_file_access("tenant_1", p_a, base_dir=root))
            self.assertFalse(validate_tenant_file_access("tenant_1", p_b, base_dir=root))

            # Path traversal attempt is blocked
            with self.assertRaises(ValueError):
                sanitize_filename("../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
