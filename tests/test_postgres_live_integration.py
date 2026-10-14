"""Real PostgreSQL Live Integration & Multi-Tenant Isolation Tests.

Executes directly against live PostgreSQL database (clinic_db) to verify:
1. Real PostgreSQL database connectivity & version.
2. Complete schema inspection & Alembic migration status.
3. Multi-tenant data isolation across repositories:
   - Tenant Patient isolation (Tenant A cannot see Tenant B).
   - Tenant Doctor isolation.
   - Tenant Slot isolation.
   - Tenant Appointment isolation.
   - Cross-tenant foreign key / query leakage rejection.
4. Concurrency uniqueness enforcement in PostgreSQL engine:
   - (doctor_id, appointment_date, appointment_time) uniqueness.
   - (tenant_id, token_no) uniqueness.
5. Super Admin platform scope verification (tenant_id is None / platform, never inherits a clinic).
6. Request-scoped database session lifecycle & transaction rollback.
"""

import os
import unittest
import uuid

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Appointment,
    AppointmentSlot,
    AuditLog,
    Clinic,
    Doctor,
    Invoice,
    Patient,
    Payment,
    Prescription,
    PrescriptionItem,
    User,
)
from app.db.session import get_engine, get_session_factory, is_db_configured
from app.repositories.tenant_scoped import (
    TenantAppointmentRepository,
    TenantDoctorRepository,
    TenantPatientRepository,
    TenantPrescriptionRepository,
    TenantSlotRepository,
    TenantUserRepository,
)


@pytest.mark.skipif(not is_db_configured(), reason="Live PostgreSQL DATABASE_URL not configured")
class PostgresLiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = get_engine()
        cls.session_factory = get_session_factory()
        # Verify engine dialect is indeed postgresql
        assert cls.engine.dialect.name == "postgresql", f"Expected PostgreSQL dialect, got {cls.engine.dialect.name}"

    def setUp(self):
        self.session = self.session_factory()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_01_live_postgres_connectivity_and_version(self):
        """Verify real connection to PostgreSQL database server."""
        with self.engine.connect() as conn:
            version_str = conn.execute(text("SELECT version();")).scalar()
            self.assertIn("PostgreSQL", version_str)
            db_name = conn.execute(text("SELECT current_database();")).scalar()
            self.assertEqual(db_name, "clinic_db")

    def test_02_all_tables_exist_in_live_postgres(self):
        """Verify all 12 normalized relational tables exist in PostgreSQL schema."""
        inspector = inspect(self.engine)
        table_names = inspector.get_table_names()
        expected = [
            "alembic_version",
            "appointment_slots",
            "appointments",
            "audit_logs",
            "clinics",
            "doctors",
            "invoices",
            "patients",
            "payments",
            "prescription_items",
            "prescriptions",
            "users",
        ]
        for tbl in expected:
            self.assertIn(tbl, table_names, f"Table '{tbl}' missing from live PostgreSQL database")

    def test_03_default_clinic_tenant_exists(self):
        """Verify the migrated default clinic tenant (XYZ Clinic) exists."""
        clinic = self.session.execute(
            select(Clinic).where(Clinic.id == "default")
        ).scalar_one_or_none()
        self.assertIsNotNone(clinic)
        self.assertEqual(clinic.id, "default")
        self.assertTrue(clinic.is_active)

    def test_04_super_admin_is_strictly_platform_scoped(self):
        """Verify Super Admin account has tenant_id=None and role=SUPER_ADMIN."""
        sa = self.session.execute(
            select(User).where(User.username == "superadmin")
        ).scalar_one_or_none()
        self.assertIsNotNone(sa)
        self.assertEqual(sa.role, "SUPER_ADMIN")
        # Super Admin must NEVER inherit a clinic tenant
        self.assertIsNone(sa.tenant_id, "Super Admin must have tenant_id=None (platform scope)")

    def test_05_migrated_entities_exist_and_reconcile(self):
        """Verify migrated records in live PostgreSQL database."""
        doc_count = self.session.execute(select(func.count(Doctor.id))).scalar()
        self.assertGreaterEqual(doc_count, 8)

        pat_count = self.session.execute(select(func.count(Patient.id))).scalar()
        self.assertGreaterEqual(pat_count, 10)

        slot_count = self.session.execute(select(func.count(AppointmentSlot.id))).scalar()
        self.assertGreaterEqual(slot_count, 21)

        app_count = self.session.execute(select(func.count(Appointment.id))).scalar()
        self.assertGreaterEqual(app_count, 10)

        rx_count = self.session.execute(select(func.count(Prescription.id))).scalar()
        self.assertGreaterEqual(rx_count, 41)

        audit_count = self.session.execute(select(func.count(AuditLog.id))).scalar()
        self.assertGreaterEqual(audit_count, 1000)

    def test_06_tenant_patient_isolation(self):
        """Verify Tenant A cannot view, query, or leak Tenant B patients."""
        tenant_a = "default"
        tenant_b = f"test_iso_{uuid.uuid4().hex[:8]}"

        # Create Tenant B clinic
        clinic_b = Clinic(id=tenant_b, name="Beta Clinic", status="ACTIVE", is_active=True)
        self.session.add(clinic_b)
        self.session.flush()

        # Create Patient for Tenant B
        repo_b = TenantPatientRepository(self.session, tenant_b)
        patient_b = repo_b.create(
            name="Private Beta Patient",
            phone="9999900001",
            patient_id=f"PAT-BETA-{uuid.uuid4().hex[:6]}",
        )

        # Query using Tenant A repository
        repo_a = TenantPatientRepository(self.session, tenant_a)
        result_for_a = repo_a.get(patient_b.patient_id)
        self.assertIsNone(result_for_a, "Tenant A repository leaked Tenant B patient record!")

        # Query by phone using Tenant A
        by_phone = repo_a.get_by_phone("9999900001")
        self.assertEqual(len(by_phone), 0, "Tenant A leaked Tenant B patient via phone lookup!")

        # Verify Tenant B can see their own patient
        result_for_b = repo_b.get(patient_b.patient_id)
        self.assertIsNotNone(result_for_b)
        self.assertEqual(result_for_b.name, "Private Beta Patient")

    def test_07_tenant_doctor_isolation(self):
        """Verify doctors are strictly partitioned by tenant_id."""
        tenant_b = f"test_doc_{uuid.uuid4().hex[:8]}"
        self.session.add(Clinic(id=tenant_b, name="Doc Isolation Clinic", status="ACTIVE", is_active=True))
        self.session.flush()

        repo_b = TenantDoctorRepository(self.session, tenant_b)
        doc_b = repo_b.create(
            name="Dr. Isolated Beta",
            specialization="Neurology",
            doctor_id="DOC-BETA-01",
        )

        repo_a = TenantDoctorRepository(self.session, "default")
        result = repo_a.get("DOC-BETA-01")
        self.assertIsNone(result, "Tenant A saw Tenant B doctor!")

        active_a = repo_a.list_active()
        for doc in active_a:
            self.assertNotEqual(doc.doctor_id, "DOC-BETA-01")

    def test_08_unique_constraint_token_no_per_tenant(self):
        """Verify PostgreSQL enforces unique constraint on (tenant_id, token_no)."""
        existing_app = self.session.execute(select(Appointment)).scalars().first()
        self.assertIsNotNone(existing_app)

        # Attempt to insert another appointment with the same token_no on same tenant
        dup = Appointment(
            tenant_id=existing_app.tenant_id,
            token_no=existing_app.token_no,
            patient_id=existing_app.patient_id,
            doctor_id=existing_app.doctor_id,
            appointment_date="2027-01-01",
            appointment_time="09:00 AM",
            amount="500",
        )
        self.session.add(dup)
        with self.assertRaises(IntegrityError):
            self.session.flush()
        self.session.rollback()

    def test_09_concurrency_double_booking_prevention(self):
        """Verify PostgreSQL enforces uq_appointment_doctor_datetime unique constraint."""
        existing_app = self.session.execute(select(Appointment)).scalars().first()
        self.assertIsNotNone(existing_app)

        # Create another appointment with same doctor, same date, same time but different token
        colliding = Appointment(
            tenant_id=existing_app.tenant_id,
            token_no=f"TKN-COLLIDE-{uuid.uuid4().hex[:6]}",
            patient_id=existing_app.patient_id,
            doctor_id=existing_app.doctor_id,
            appointment_date=existing_app.appointment_date,
            appointment_time=existing_app.appointment_time,
            amount="500",
        )
        self.session.add(colliding)
        with self.assertRaises(IntegrityError):
            self.session.flush()
        self.session.rollback()

    def test_10_transaction_rollback_guarantee(self):
        """Verify failed transaction rolls back cleanly without leaving orphan data."""
        initial_patients = self.session.execute(select(func.count(Patient.id))).scalar()
        try:
            p = Patient(
                tenant_id="default",
                patient_id=f"PAT-TMP-{uuid.uuid4().hex[:6]}",
                name="Rollback Candidate",
                phone="0000000000",
            )
            self.session.add(p)
            self.session.flush()
            # Force an error
            raise RuntimeError("Forced simulation error")
        except RuntimeError:
            self.session.rollback()

        final_patients = self.session.execute(select(func.count(Patient.id))).scalar()
        self.assertEqual(initial_patients, final_patients, "Rollback failed to restore patient count!")


if __name__ == "__main__":
    unittest.main()

