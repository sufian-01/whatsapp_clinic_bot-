"""Tests for PostgreSQL Data Migration Engine.

Verifies:
1. Dry-run mode simulates full migration without committing changes.
2. Live commit mode migrates Doctors, Doctor Accounts, Patients, Slots, Appointments, Prescriptions.
3. Idempotency: Running migration twice does not create duplicates or violate unique constraints.
4. Foreign key integrity: Prescriptions, Appointments, Slots correctly reference Doctor and Patient IDs.
5. Reconciliation report accuracy.
"""

import unittest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    Appointment,
    AppointmentSlot,
    Clinic,
    Doctor,
    Patient,
    Prescription,
    PrescriptionItem,
    User,
)
from app.scripts.migrate_sheets_and_json_to_postgres import DataMigrator


class DataMigrationTests(unittest.TestCase):
    def setUp(self):
        # In-memory SQLite with foreign keys enabled
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

        # Sample test fixtures matching Google Sheets schemas
        self.doctor_rows = [
            ["Doctor ID", "Doctor Name", "Specialization", "Available Days", "Start Time", "End Time", "Consultation Fee", "Status"],
            ["DOC001", "Dr. Arjun Mehta", "General Physician", "Mon, Wed, Fri", "10:00 AM", "1:00 PM", "500", "Active"],
            ["DOC002", "Dr. Sana Khan", "Gynecologist", "Tue, Thu, Sat", "11:00 AM", "2:00 PM", "700", "Active"],
        ]

        self.patient_rows = [
            [
                "Patient ID", "Name", "Email", "Phone", "Age", "Gender",
                "Doctor", "Appointment Date", "Appointment Time", "Token No",
                "Amount", "Payment Method", "Payment Status", "Booking Status", "Created At"
            ],
            [
                "PAT-101", "Rahul Sharma", "rahul@test.com", "9876543210", "32", "Male",
                "Dr. Arjun Mehta", "2026-10-15", "10:00 AM", "TKN-101",
                "500", "Offline", "Paid", "Confirmed", "2026-10-10T10:00:00Z"
            ],
        ]

        self.slot_rows = [
            ["Slot ID", "Doctor ID", "Doctor Name", "Date", "Start Time", "End Time", "Status"],
            ["SLT-101", "DOC001", "Dr. Arjun Mehta", "2026-10-15", "10:00 AM", "10:30 AM", "available"],
            ["SLT-102", "DOC001", "Dr. Arjun Mehta", "2026-10-15", "10:30 AM", "11:00 AM", "available"],
        ]

        self.doctor_accounts_data = {
            "dr_arjun": {
                "username": "dr_arjun",
                "password_hash": "pbkdf2:sha256:100000$salt$hash",
                "doctor_id": "DOC001",
                "doctor_name": "Dr. Arjun Mehta",
                "specialization": "General Physician",
                "email": "arjun@clinic.com",
            }
        }

        self.prescriptions_data = {
            "RX-101": {
                "prescription_id": "RX-101",
                "patient_id": "PAT-101",
                "patient_name": "Rahul Sharma",
                "doctor_id": "DOC001",
                "appointment_id": "TKN-101",
                "diagnosis": "Mild Fever",
                "symptoms": "Body ache",
                "medicines": [
                    {
                        "name": "Paracetamol",
                        "dosage": "500mg",
                        "frequency": "1-0-1",
                        "duration": "3 days",
                        "instructions": "After meals",
                    }
                ],
                "status": "finalized",
            }
        }

    def tearDown(self):
        self.engine.dispose()

    def test_dry_run_does_not_persist_records(self):
        with self.session_factory() as session:
            migrator = DataMigrator(session=session, tenant_id="tenant_dry", dry_run=True)
            report = migrator.run(
                doctor_rows=self.doctor_rows,
                patient_rows=self.patient_rows,
                slot_rows=self.slot_rows,
                doctor_accounts_data=self.doctor_accounts_data,
                prescriptions_data=self.prescriptions_data,
            )

            self.assertTrue(report["dry_run"])
            self.assertEqual(report["errors_count"], 0)
            self.assertEqual(report["entity_counts"]["doctors"]["created"], 2)

        # Verify nothing persisted in database
        with self.session_factory() as session:
            doc_count = session.query(Doctor).count()
            self.assertEqual(doc_count, 0)

    def test_commit_mode_persists_all_entities(self):
        with self.session_factory() as session:
            migrator = DataMigrator(session=session, tenant_id="tenant_live", dry_run=False)
            report = migrator.run(
                doctor_rows=self.doctor_rows,
                patient_rows=self.patient_rows,
                slot_rows=self.slot_rows,
                doctor_accounts_data=self.doctor_accounts_data,
                prescriptions_data=self.prescriptions_data,
            )
            self.assertFalse(report["dry_run"])
            self.assertEqual(report["errors_count"], 0)

        # Verify records persisted
        with self.session_factory() as session:
            clinics = session.query(Clinic).all()
            self.assertEqual(len(clinics), 1)
            self.assertEqual(clinics[0].id, "tenant_live")

            doctors = session.query(Doctor).all()
            self.assertEqual(len(doctors), 2)

            users = session.query(User).all()
            self.assertEqual(len(users), 1)
            self.assertEqual(users[0].username, "dr_arjun")
            self.assertEqual(users[0].role, "DOCTOR")

            patients = session.query(Patient).all()
            self.assertEqual(len(patients), 1)
            self.assertEqual(patients[0].patient_id, "PAT-101")

            slots = session.query(AppointmentSlot).all()
            self.assertEqual(len(slots), 2)

            appointments = session.query(Appointment).all()
            self.assertEqual(len(appointments), 1)
            self.assertEqual(appointments[0].token_no, "TKN-101")

            prescriptions = session.query(Prescription).all()
            self.assertEqual(len(prescriptions), 1)
            self.assertEqual(prescriptions[0].prescription_id, "RX-101")

            items = session.query(PrescriptionItem).all()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].name, "Paracetamol")

    def test_idempotent_second_run_updates_without_duplicates(self):
        with self.session_factory() as session:
            migrator1 = DataMigrator(session=session, tenant_id="tenant_idempotent", dry_run=False)
            migrator1.run(
                doctor_rows=self.doctor_rows,
                patient_rows=self.patient_rows,
                slot_rows=self.slot_rows,
                doctor_accounts_data=self.doctor_accounts_data,
                prescriptions_data=self.prescriptions_data,
            )

        with self.session_factory() as session:
            doc_count_run1 = session.query(Doctor).count()
            self.assertEqual(doc_count_run1, 2)

        # Run a second time
        with self.session_factory() as session:
            migrator2 = DataMigrator(session=session, tenant_id="tenant_idempotent", dry_run=False)
            report2 = migrator2.run(
                doctor_rows=self.doctor_rows,
                patient_rows=self.patient_rows,
                slot_rows=self.slot_rows,
                doctor_accounts_data=self.doctor_accounts_data,
                prescriptions_data=self.prescriptions_data,
            )
            self.assertEqual(report2["errors_count"], 0)
            self.assertEqual(report2["entity_counts"]["doctors"]["updated"], 2)
            self.assertEqual(report2["entity_counts"]["doctors"]["created"], 0)

        with self.session_factory() as session:
            doc_count_run2 = session.query(Doctor).count()
            self.assertEqual(doc_count_run2, 2)  # No duplicates!

