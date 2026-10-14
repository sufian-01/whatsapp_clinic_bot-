"""Tests for Phase 1B Database and Alembic Foundation.

Verifies:
1. Database configuration in Settings and validation.
2. SQLAlchemy 2.x Base and model metadata.
3. Domain models and relational integrity.
4. Concurrency uniqueness constraints for slots and appointments.
5. Session management, engine pooling, and get_db dependency.
6. Alembic configuration and migration metadata.
"""

from datetime import datetime, timezone
from pathlib import Path
import unittest
import uuid

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, validate_settings
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
    get_db,
    get_engine,
    get_session_factory,
    is_db_configured,
    normalize_database_url,
    reset_db_state,
)


class Phase1bDatabaseTests(unittest.TestCase):
    def setUp(self):
        reset_db_state()

    def tearDown(self):
        reset_db_state()

    # -------------------------------------------------------------------------
    # 1. Configuration Tests
    # -------------------------------------------------------------------------
    def test_database_url_setting_defaults_to_empty(self):
        settings = Settings(
            clinic_name="Clinic",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
        )
        self.assertEqual(settings.database_url, "")
        self.assertFalse(is_db_configured(settings.database_url))

    def test_database_url_validation_accepts_valid_urls(self):
        for valid_url in (
            "postgresql://user:pass@localhost:5432/db",
            "postgresql+psycopg://user:pass@localhost:5432/db",
            "postgresql+psycopg2://user:pass@localhost:5432/db",
            "sqlite:///:memory:",
        ):
            settings = Settings(
                clinic_name="Clinic",
                telegram_bot_token="tok",
                telegram_webhook_secret="sec",
                gemini_api_key="key",
                gemini_model="mod",
                telegram_webhook_url="url",
                knowledge_dir=Path("k"),
                vectorstore_dir=Path("v"),
                database_url=valid_url,
            )
            validate_settings(settings)

    def test_database_url_validation_rejects_invalid_urls(self):
        settings = Settings(
            clinic_name="Clinic",
            telegram_bot_token="tok",
            telegram_webhook_secret="sec",
            gemini_api_key="key",
            gemini_model="mod",
            telegram_webhook_url="url",
            knowledge_dir=Path("k"),
            vectorstore_dir=Path("v"),
            database_url="mysql://user:pass@localhost:3306/db",
        )
        with self.assertRaises(RuntimeError) as ctx:
            validate_settings(settings)
        self.assertIn("Invalid DATABASE_URL format", str(ctx.exception))

    def test_normalize_database_url_converts_legacy_postgres_prefix(self):
        self.assertEqual(
            normalize_database_url("postgresql://user:pass@localhost/db"),
            "postgresql+psycopg://user:pass@localhost/db",
        )
        self.assertEqual(
            normalize_database_url("postgres://user:pass@localhost/db"),
            "postgresql+psycopg://user:pass@localhost/db",
        )
        self.assertEqual(
            normalize_database_url("sqlite:///:memory:"),
            "sqlite:///:memory:",
        )

    # -------------------------------------------------------------------------
    # 2. Metadata & Model Table Registration
    # -------------------------------------------------------------------------
    def test_base_metadata_contains_all_core_domain_tables(self):
        expected_tables = {
            "clinics",
            "users",
            "doctors",
            "patients",
            "appointment_slots",
            "appointments",
            "prescriptions",
            "prescription_items",
            "invoices",
            "payments",
            "audit_logs",
        }
        actual_tables = set(Base.metadata.tables.keys())
        self.assertTrue(
            expected_tables.issubset(actual_tables),
            f"Missing tables: {expected_tables - actual_tables}",
        )

    # -------------------------------------------------------------------------
    # 3. ORM Schema and Relational Tests
    # -------------------------------------------------------------------------
    def test_orm_models_can_be_created_and_queried(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            # 1. Create Clinic
            clinic = Clinic(
                name="Metro Health Clinic",
                timezone="Asia/Kolkata",
                phone="6200126662",
                upi_id="metro@upi",
            )
            session.add(clinic)
            session.flush()

            # 2. Create Doctor
            doctor = Doctor(
                clinic_id=clinic.id,
                doctor_id="DOC-01",
                name="Dr. Sarah Johnson",
                specialization="Cardiology",
                status="Active",
            )
            session.add(doctor)
            session.flush()

            # 3. Create Patient
            patient = Patient(
                clinic_id=clinic.id,
                patient_id="PAT-01",
                name="Alice Smith",
                phone="+919876543210",
                email="alice@example.com",
            )
            session.add(patient)
            session.flush()

            # 4. Create Slot
            slot = AppointmentSlot(
                clinic_id=clinic.id,
                slot_id="SLT-01",
                doctor_id=doctor.id,
                date="2026-10-15",
                start_time="10:00",
                end_time="10:30",
                status="available",
            )
            session.add(slot)
            session.flush()

            # 5. Create Appointment linked to Patient, Doctor, Slot
            appt = Appointment(
                clinic_id=clinic.id,
                token_no="TKN-001",
                patient_id=patient.id,
                doctor_id=doctor.id,
                slot_id=slot.id,
                appointment_date="2026-10-15",
                appointment_time="10:00",
                amount="500",
                booking_status="Confirmed",
            )
            session.add(appt)
            session.flush()

            # 6. Create Prescription with normalized Items
            rx = Prescription(
                clinic_id=clinic.id,
                prescription_id="RX-001",
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_id=appt.id,
                date="2026-10-15",
                diagnosis="Hypertension",
                status="finalized",
            )
            item1 = PrescriptionItem(
                prescription_id=rx.id,
                order_index=1,
                name="Amlodipine",
                dosage="5mg",
                frequency="1-0-0",
                duration="30 days",
            )
            rx.items.append(item1)
            session.add(rx)
            session.flush()

            # 7. Create Invoice and Payment
            inv = Invoice(
                clinic_id=clinic.id,
                invoice_number="INV-001",
                appointment_id=appt.id,
                patient_id=patient.id,
                amount="500",
                payment_status="Pending",
            )
            session.add(inv)
            session.flush()

            pay = Payment(
                clinic_id=clinic.id,
                payment_id="PAY-001",
                appointment_id=appt.id,
                invoice_id=inv.id,
                amount="500",
                payment_method="UPI",
                payment_status="Completed",
            )
            session.add(pay)

            # 8. Create User & Audit Log
            user = User(
                clinic_id=clinic.id,
                username="dr_sarah",
                password_hash="pbkdf2:dummy",
                doctor_id="DOC-01",
                role="doctor",
            )
            audit = AuditLog(
                clinic_id=clinic.id,
                audit_id="AUD-001",
                user="admin",
                action="TEST_ACTION",
                entity_type="clinic",
                entity_id=clinic.id,
            )
            session.add_all([user, audit])
            session.commit()

        # Query and verify relationships in fresh session
        with Session(engine) as session:
            queried_doctor = session.query(Doctor).filter_by(doctor_id="DOC-01").one()
            self.assertEqual(len(queried_doctor.slots), 1)
            self.assertEqual(queried_doctor.slots[0].start_time, "10:00")

            queried_appt = session.query(Appointment).filter_by(token_no="TKN-001").one()
            self.assertEqual(queried_appt.patient.name, "Alice Smith")
            self.assertEqual(queried_appt.doctor.name, "Dr. Sarah Johnson")

            queried_rx = session.query(Prescription).filter_by(prescription_id="RX-001").one()
            self.assertEqual(len(queried_rx.items), 1)
            self.assertEqual(queried_rx.items[0].name, "Amlodipine")

    # -------------------------------------------------------------------------
    # 4. Concurrency Constraints Verification
    # -------------------------------------------------------------------------
    def test_appointment_slot_unique_constraint_prevents_duplicate_slot(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            doc = Doctor(doctor_id="DOC-U1", name="Dr. Unique", specialization="General")
            session.add(doc)
            session.flush()

            # First slot
            s1 = AppointmentSlot(
                slot_id="SLT-U1",
                doctor_id=doc.id,
                date="2026-10-20",
                start_time="09:00",
                end_time="09:30",
            )
            session.add(s1)
            session.commit()

            # Second slot with exact same doctor, date, start_time -> must fail
            s2 = AppointmentSlot(
                slot_id="SLT-U2",
                doctor_id=doc.id,
                date="2026-10-20",
                start_time="09:00",
                end_time="09:30",
            )
            session.add(s2)
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_appointment_unique_constraint_prevents_double_booking(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            doc = Doctor(doctor_id="DOC-B1", name="Dr. Booking", specialization="General")
            p1 = Patient(patient_id="PAT-B1", name="Patient 1", phone="111")
            p2 = Patient(patient_id="PAT-B2", name="Patient 2", phone="222")
            session.add_all([doc, p1, p2])
            session.flush()

            # Booking 1
            a1 = Appointment(
                token_no="TKN-B1",
                patient_id=p1.id,
                doctor_id=doc.id,
                appointment_date="2026-10-25",
                appointment_time="11:00",
            )
            session.add(a1)
            session.commit()

            # Booking 2 with same doctor, date, time -> must fail
            a2 = Appointment(
                token_no="TKN-B2",
                patient_id=p2.id,
                doctor_id=doc.id,
                appointment_date="2026-10-25",
                appointment_time="11:00",
            )
            session.add(a2)
            with self.assertRaises(IntegrityError):
                session.commit()

    # -------------------------------------------------------------------------
    # 5. Session Factory and get_db Dependency
    # -------------------------------------------------------------------------
    def test_get_engine_fails_gracefully_when_unconfigured(self):
        with self.assertRaises(RuntimeError) as ctx:
            get_engine(database_url="")
        self.assertIn("DATABASE_URL is not configured", str(ctx.exception))

    def test_get_db_yields_working_session(self):
        test_url = "sqlite:///:memory:"
        engine = get_engine(test_url)
        Base.metadata.create_all(engine)

        gen = get_db(test_url)
        session = next(gen)
        self.assertIsInstance(session, Session)

        # Create record inside session
        clinic = Clinic(name="Yielded Clinic")
        session.add(clinic)
        try:
            next(gen)
        except StopIteration:
            pass  # Expected when generator finishes

        # Verify record committed
        factory = get_session_factory(test_url)
        with factory() as check_session:
            self.assertIsNotNone(check_session.query(Clinic).filter_by(name="Yielded Clinic").first())

    # -------------------------------------------------------------------------
    # 6. Alembic Setup Verification
    # -------------------------------------------------------------------------
    def test_alembic_configuration_and_migrations_exist(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "alembic.ini").exists())
        self.assertTrue((root / "alembic" / "env.py").exists())
        versions = list((root / "alembic" / "versions").glob("*.py"))
        self.assertGreater(len(versions), 0, "Expected at least one initial Alembic migration.")


if __name__ == "__main__":
    unittest.main()

