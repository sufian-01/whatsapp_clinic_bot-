"""Repeatable, Idempotent Data Migration: Google Sheets & JSON -> PostgreSQL.

Migrates legacy persistent data into normalized SQLAlchemy 2.x relational tables:
- Clinic Tenant (Clinics)
- Admin Accounts (Platform Super Admin & Clinic Admin Users)
- Doctor Directory & Accounts (Doctors & Users)
- Patient Directory (Patients)
- Appointment Slots (AppointmentSlots)
- Appointments & Booking Records (Appointments)
- Invoices & Payments (Invoices & Payments)
- Prescriptions & Medication Line Items (Prescriptions & PrescriptionItems)
- Audit Logs (AuditLogs)

Features:
- Dry-run mode by default (--dry-run or programmatic dry_run=True).
- Duplicate detection & stable primary identifier resolution.
- Foreign key & relationship validation.
- Tenant scoping on every record.
- Non-destructive: Never modifies or clears source Google Sheets or JSON files.
- Generates structured reconciliation report (record counts, diffs, warnings, database row counts).
"""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import uuid

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.auth import hash_password
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
from app.db.session import get_engine, get_session_factory

logger = logging.getLogger("migration")


class MigrationReport:
    def __init__(self, tenant_id: str, dry_run: bool):
        self.tenant_id = tenant_id
        self.dry_run = dry_run
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        self.entity_counts: Dict[str, Dict[str, int]] = {
            "clinics": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "admin_users": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "doctors": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "doctor_accounts": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "patients": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "slots": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "appointments": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "invoices": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "payments": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "prescriptions": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "prescription_items": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "audit_logs": {"source": 0, "created": 0, "updated": 0, "skipped": 0},
            "duplicates": {"appointments": 0, "slots": 0, "patients": 0},
        }
        self.final_database_counts: Dict[str, int] = {}
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[str] = []

    def record_action(self, entity: str, action: str):
        if entity in self.entity_counts and action in self.entity_counts[entity]:
            self.entity_counts[entity][action] += 1

    def add_error(self, entity: str, identifier: str, reason: str):
        self.errors.append({"entity": entity, "identifier": identifier, "reason": reason})

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "dry_run": self.dry_run,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "entity_counts": self.entity_counts,
            "final_database_counts": self.final_database_counts,
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
        }


class DataMigrator:
    """Idempotent orchestrator to migrate Sheets and JSON data into PostgreSQL."""

    def __init__(
        self,
        session: Session,
        tenant_id: str = "default",
        clinic_name: str = "XYZ Clinic",
        dry_run: bool = True,
        data_dir: Optional[Path] = None,
    ):
        self.session = session
        self.tenant_id = tenant_id.strip()
        self.clinic_name = clinic_name.strip()
        self.dry_run = dry_run
        self.data_dir = data_dir or (Path(__file__).resolve().parents[2] / "data")
        self.report = MigrationReport(tenant_id=self.tenant_id, dry_run=self.dry_run)

        # Lookup caches: maps human identifiers to database UUIDs
        self.doctor_uuid_by_doc_id: Dict[str, str] = {}
        self.patient_uuid_by_patient_id: Dict[str, str] = {}
        self.slot_uuid_by_slot_id: Dict[str, str] = {}
        self.appointment_uuid_by_token: Dict[str, str] = {}

    def run(
        self,
        doctor_rows: Optional[List[List[str]]] = None,
        patient_rows: Optional[List[List[str]]] = None,
        slot_rows: Optional[List[List[str]]] = None,
        doctor_accounts_data: Optional[Dict[str, Any]] = None,
        prescriptions_data: Optional[Dict[str, Any]] = None,
        include_audit_logs: bool = False,
        include_admin_users: bool = False,
        include_invoices_and_payments: bool = False,
    ) -> Dict[str, Any]:
        """Execute end-to-end migration."""
        try:
            # 1. Ensure Clinic Tenant Record exists
            self.migrate_clinic()

            # 2. Ensure Admin User Accounts exist (Super Admin & Tenant Admin)
            if include_admin_users:
                self.migrate_admin_accounts()

            # 3. Migrate Doctors
            self.migrate_doctors(doctor_rows)

            # 4. Migrate Doctor User Accounts
            self.migrate_doctor_accounts(doctor_accounts_data)

            # 5. Migrate Patients
            self.migrate_patients(patient_rows)

            # 6. Migrate Slots
            self.migrate_slots(slot_rows)

            # 7. Migrate Appointments
            self.migrate_appointments(patient_rows)

            # 8. Migrate Invoices & Payments corresponding to appointments
            if include_invoices_and_payments:
                self.migrate_invoices_and_payments()

            # 9. Migrate Prescriptions
            self.migrate_prescriptions(prescriptions_data)

            # 10. Migrate Audit Logs
            if include_audit_logs:
                self.migrate_audit_logs()

            self.report.completed_at = datetime.now(timezone.utc).isoformat()

            if self.dry_run:
                self.session.rollback()
                logger.info("Dry-run migration complete. All database operations rolled back.")
            else:
                self.session.commit()
                logger.info("Migration successfully committed to the database.")
                self.report.final_database_counts = self.query_final_counts()

        except Exception as e:
            self.session.rollback()
            logger.error("Migration failed with fatal exception: %s", e)
            self.report.add_error("general", "transaction", str(e))
            self.report.completed_at = datetime.now(timezone.utc).isoformat()

        return self.report.to_dict()

    def query_final_counts(self) -> Dict[str, int]:
        """Query actual live row counts in the database for verification."""
        counts = {}
        for model, name in [
            (Clinic, "clinics"),
            (User, "users"),
            (Doctor, "doctors"),
            (Patient, "patients"),
            (AppointmentSlot, "appointment_slots"),
            (Appointment, "appointments"),
            (Prescription, "prescriptions"),
            (PrescriptionItem, "prescription_items"),
            (Invoice, "invoices"),
            (Payment, "payments"),
            (AuditLog, "audit_logs"),
        ]:
            try:
                cnt = self.session.execute(select(func.count(model.id))).scalar() or 0
                counts[name] = cnt
            except Exception:
                counts[name] = 0
        return counts

    def migrate_clinic(self) -> Clinic:
        """Ensure the target clinic facility exists."""
        stmt = select(Clinic).where(Clinic.id == self.tenant_id)
        clinic = self.session.execute(stmt).scalar_one_or_none()
        if not clinic:
            clinic = Clinic(
                id=self.tenant_id,
                name=self.clinic_name,
                legal_name=self.clinic_name,
                status="ACTIVE",
                is_active=True,
            )
            self.session.add(clinic)
            self.session.flush()
            self.report.record_action("clinics", "created")
        else:
            self.report.record_action("clinics", "skipped")
        self.report.entity_counts["clinics"]["source"] = 1
        return clinic

    def migrate_admin_accounts(self):
        """Ensure default Super Admin and Tenant Admin accounts exist."""
        try:
            settings = get_settings()
        except Exception:
            return

        # 1. Super Admin (Platform scope: tenant_id=None, role='SUPER_ADMIN')
        sa_user = (getattr(settings, "super_admin_username", "superadmin") or "superadmin").strip().casefold()
        stmt = select(User).where(User.username == sa_user)
        existing_sa = self.session.execute(stmt).scalar_one_or_none()
        if existing_sa:
            self.report.record_action("admin_users", "skipped")
        else:
            sa_pw = getattr(settings, "super_admin_password", "superadmin123") or "superadmin123"
            sa_hash = getattr(settings, "super_admin_password_hash", "") or hash_password(sa_pw)
            new_sa = User(
                tenant_id=None,
                username=sa_user,
                password_hash=sa_hash,
                role="SUPER_ADMIN",
                full_name="Super Administrator",
                email="superadmin@clinic.local",
                is_active=True,
                must_change_password=False,
            )
            self.session.add(new_sa)
            self.session.flush()
            self.report.record_action("admin_users", "created")

        # 2. Tenant Admin (Tenant scope: tenant_id=self.tenant_id, role='TENANT_ADMIN')
        ta_user = (getattr(settings, "crm_admin_username", "admin") or "admin").strip().casefold()
        stmt_ta = select(User).where(User.tenant_id == self.tenant_id, User.username == ta_user)
        existing_ta = self.session.execute(stmt_ta).scalar_one_or_none()
        if existing_ta:
            self.report.record_action("admin_users", "skipped")
        else:
            ta_pw = getattr(settings, "crm_admin_password", "admin123") or "admin123"
            ta_hash = getattr(settings, "crm_admin_password_hash", "") or hash_password(ta_pw)
            new_ta = User(
                tenant_id=self.tenant_id,
                username=ta_user,
                password_hash=ta_hash,
                role="TENANT_ADMIN",
                full_name=f"{self.clinic_name} Admin",
                email="admin@clinic.local",
                is_active=True,
                must_change_password=False,
            )
            self.session.add(new_ta)
            self.session.flush()
            self.report.record_action("admin_users", "created")
        self.report.entity_counts["admin_users"]["source"] = 2

    def migrate_doctors(self, doctor_rows: Optional[List[List[str]]] = None):
        """Migrate Doctor rows."""
        rows = doctor_rows or self._load_sheet_rows_from_cache("doctors")
        if not rows:
            return

        self.report.entity_counts["doctors"]["source"] = max(0, len(rows) - 1)
        header = [h.strip().casefold() for h in rows[0]]

        def idx_of(names: List[str]) -> Optional[int]:
            for n in names:
                if n.casefold() in header:
                    return header.index(n.casefold())
            return None

        doc_id_idx = idx_of(["doctor id", "id"])
        name_idx = idx_of(["doctor name", "name"])
        spec_idx = idx_of(["specialization", "specialty"])
        days_idx = idx_of(["available days", "days"])
        start_idx = idx_of(["start time", "start"])
        end_idx = idx_of(["end time", "end"])
        fee_idx = idx_of(["consultation fee", "fee"])
        status_idx = idx_of(["status"])

        for row in rows[1:]:
            if not row or not any(row):
                continue
            doc_id = row[doc_id_idx].strip() if doc_id_idx is not None and doc_id_idx < len(row) else ""
            name = row[name_idx].strip() if name_idx is not None and name_idx < len(row) else ""
            if not doc_id or not name:
                self.report.add_error("doctors", str(row), "Missing required doctor ID or name")
                continue

            spec = row[spec_idx].strip() if spec_idx is not None and spec_idx < len(row) else "General Physician"
            fee = row[fee_idx].strip() if fee_idx is not None and fee_idx < len(row) else "500"
            days = row[days_idx].strip() if days_idx is not None and days_idx < len(row) else ""
            start = row[start_idx].strip() if start_idx is not None and start_idx < len(row) else ""
            end = row[end_idx].strip() if end_idx is not None and end_idx < len(row) else ""
            st = row[status_idx].strip() if status_idx is not None and status_idx < len(row) else "Active"

            stmt = select(Doctor).where(Doctor.tenant_id == self.tenant_id, Doctor.doctor_id == doc_id)
            existing = self.session.execute(stmt).scalar_one_or_none()

            if existing:
                existing.name = name
                existing.specialization = spec
                existing.consultation_fee = fee
                existing.available_days = days
                existing.start_time = start
                existing.end_time = end
                existing.status = st
                self.doctor_uuid_by_doc_id[doc_id] = existing.id
                self.report.record_action("doctors", "updated")
            else:
                doc = Doctor(
                    tenant_id=self.tenant_id,
                    doctor_id=doc_id,
                    name=name,
                    specialization=spec,
                    consultation_fee=fee,
                    available_days=days,
                    start_time=start,
                    end_time=end,
                    status=st,
                )
                self.session.add(doc)
                self.session.flush()
                self.doctor_uuid_by_doc_id[doc_id] = doc.id
                self.report.record_action("doctors", "created")

    def migrate_doctor_accounts(self, accounts_data: Optional[Dict[str, Any]] = None):
        """Migrate doctor account credentials into User model."""
        data = accounts_data
        if data is None:
            path = self.data_dir / "doctor_accounts.json"
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    self.report.add_warning(f"Could not load doctor_accounts.json: {e}")
                    data = {}
            else:
                data = {}

        if not data:
            return

        self.report.entity_counts["doctor_accounts"]["source"] = len(data)

        for username, acc in data.items():
            u_clean = username.strip().casefold()
            pw_hash = acc.get("password_hash", "")
            doc_id = acc.get("doctor_id", "")
            doc_name = acc.get("doctor_name", "")
            email = acc.get("email", "")

            stmt = select(User).where(User.username == u_clean)
            existing = self.session.execute(stmt).scalar_one_or_none()

            if existing:
                existing.tenant_id = self.tenant_id
                existing.password_hash = pw_hash
                existing.role = "DOCTOR"
                existing.doctor_id = doc_id
                existing.full_name = doc_name
                existing.email = email
                self.report.record_action("doctor_accounts", "updated")
            else:
                user = User(
                    tenant_id=self.tenant_id,
                    username=u_clean,
                    password_hash=pw_hash,
                    role="DOCTOR",
                    doctor_id=doc_id,
                    full_name=doc_name,
                    email=email,
                    is_active=True,
                )
                self.session.add(user)
                self.session.flush()
                self.report.record_action("doctor_accounts", "created")

    def migrate_patients(self, patient_rows: Optional[List[List[str]]] = None):
        """Migrate patient profiles from patient sheet."""
        rows = patient_rows or self._load_sheet_rows_from_cache("patients")
        if not rows:
            return

        self.report.entity_counts["patients"]["source"] = max(0, len(rows) - 1)
        header = [h.strip().casefold() for h in rows[0]]

        def idx_of(names: List[str]) -> Optional[int]:
            for n in names:
                if n.casefold() in header:
                    return header.index(n.casefold())
            return None

        pid_idx = idx_of(["patient id", "id"])
        name_idx = idx_of(["name", "patient name"])
        phone_idx = idx_of(["phone", "mobile"])
        email_idx = idx_of(["email"])
        age_idx = idx_of(["age"])
        gender_idx = idx_of(["gender"])

        seen_in_batch = set()

        for row in rows[1:]:
            if not row or not any(row):
                continue
            pid = row[pid_idx].strip() if pid_idx is not None and pid_idx < len(row) else ""
            name = row[name_idx].strip() if name_idx is not None and name_idx < len(row) else ""
            phone = row[phone_idx].strip() if phone_idx is not None and phone_idx < len(row) else ""

            if not pid or not name:
                continue

            if pid in seen_in_batch:
                self.report.record_action("duplicates", "patients")
                continue
            seen_in_batch.add(pid)

            email = row[email_idx].strip() if email_idx is not None and email_idx < len(row) else ""
            age = row[age_idx].strip() if age_idx is not None and age_idx < len(row) else ""
            gender = row[gender_idx].strip() if gender_idx is not None and gender_idx < len(row) else ""

            stmt = select(Patient).where(Patient.tenant_id == self.tenant_id, Patient.patient_id == pid)
            existing = self.session.execute(stmt).scalar_one_or_none()

            if existing:
                existing.name = name
                existing.phone = phone
                existing.email = email
                existing.age = age
                existing.gender = gender
                self.patient_uuid_by_patient_id[pid] = existing.id
                self.report.record_action("patients", "updated")
            else:
                pat = Patient(
                    tenant_id=self.tenant_id,
                    patient_id=pid,
                    name=name,
                    phone=phone,
                    email=email,
                    age=age,
                    gender=gender,
                )
                self.session.add(pat)
                self.session.flush()
                self.patient_uuid_by_patient_id[pid] = pat.id
                self.report.record_action("patients", "created")

    def migrate_slots(self, slot_rows: Optional[List[List[str]]] = None):
        """Migrate appointment slots."""
        rows = slot_rows or self._load_sheet_rows_from_cache("slots")
        if not rows:
            return

        self.report.entity_counts["slots"]["source"] = max(0, len(rows) - 1)
        header = [h.strip().casefold() for h in rows[0]]

        def idx_of(names: List[str]) -> Optional[int]:
            for n in names:
                if n.casefold() in header:
                    return header.index(n.casefold())
            return None

        slot_id_idx = idx_of(["slot id", "id"])
        doc_id_idx = idx_of(["doctor id"])
        date_idx = idx_of(["date"])
        start_idx = idx_of(["start time", "start"])
        end_idx = idx_of(["end time", "end"])
        status_idx = idx_of(["status"])

        for row in rows[1:]:
            if not row or not any(row):
                continue
            slot_id = row[slot_id_idx].strip() if slot_id_idx is not None and slot_id_idx < len(row) else ""
            doc_id = row[doc_id_idx].strip() if doc_id_idx is not None and doc_id_idx < len(row) else ""
            d_date = row[date_idx].strip() if date_idx is not None and date_idx < len(row) else ""
            s_time = row[start_idx].strip() if start_idx is not None and start_idx < len(row) else ""
            e_time = row[end_idx].strip() if end_idx is not None and end_idx < len(row) else ""

            if not slot_id or not doc_id:
                continue

            doc_uuid = self.doctor_uuid_by_doc_id.get(doc_id)
            if not doc_uuid:
                stmt = select(Doctor.id).where(Doctor.tenant_id == self.tenant_id, Doctor.doctor_id == doc_id)
                doc_uuid = self.session.execute(stmt).scalar_one_or_none()
                if doc_uuid:
                    self.doctor_uuid_by_doc_id[doc_id] = doc_uuid
                else:
                    self.report.add_error("slots", slot_id, f"Referenced doctor '{doc_id}' not found")
                    continue

            status_val = row[status_idx].strip().lower() if status_idx is not None and status_idx < len(row) else "available"

            stmt = select(AppointmentSlot).where(
                AppointmentSlot.tenant_id == self.tenant_id,
                AppointmentSlot.slot_id == slot_id,
            )
            existing = self.session.execute(stmt).scalar_one_or_none()

            if existing:
                existing.status = status_val
                existing.date = d_date
                existing.start_time = s_time
                existing.end_time = e_time
                self.slot_uuid_by_slot_id[slot_id] = existing.id
                self.report.record_action("slots", "updated")
            else:
                sl = AppointmentSlot(
                    tenant_id=self.tenant_id,
                    slot_id=slot_id,
                    doctor_id=doc_uuid,
                    date=d_date,
                    start_time=s_time,
                    end_time=e_time,
                    status=status_val,
                )
                self.session.add(sl)
                self.session.flush()
                self.slot_uuid_by_slot_id[slot_id] = sl.id
                self.report.record_action("slots", "created")

    def migrate_appointments(self, patient_rows: Optional[List[List[str]]] = None):
        """Migrate appointment booking records from patient sheet."""
        rows = patient_rows or self._load_sheet_rows_from_cache("patients")
        if not rows:
            return

        self.report.entity_counts["appointments"]["source"] = max(0, len(rows) - 1)
        header = [h.strip().casefold() for h in rows[0]]

        def idx_of(names: List[str]) -> Optional[int]:
            for n in names:
                if n.casefold() in header:
                    return header.index(n.casefold())
            return None

        pid_idx = idx_of(["patient id"])
        token_idx = idx_of(["token no", "token", "appointment id"])
        doc_name_idx = idx_of(["doctor", "doctor name"])
        date_idx = idx_of(["appointment date", "date"])
        time_idx = idx_of(["appointment time", "time"])
        amt_idx = idx_of(["amount"])
        pay_method_idx = idx_of(["payment method"])
        pay_status_idx = idx_of(["payment status"])
        book_status_idx = idx_of(["booking status"])

        for row in rows[1:]:
            if not row or not any(row):
                continue
            token_no = row[token_idx].strip() if token_idx is not None and token_idx < len(row) else ""
            pid = row[pid_idx].strip() if pid_idx is not None and pid_idx < len(row) else ""
            if not token_no or not pid:
                continue

            pat_uuid = self.patient_uuid_by_patient_id.get(pid)
            if not pat_uuid:
                stmt = select(Patient.id).where(Patient.tenant_id == self.tenant_id, Patient.patient_id == pid)
                pat_uuid = self.session.execute(stmt).scalar_one_or_none()
                if not pat_uuid:
                    self.report.add_error("appointments", token_no, f"Patient '{pid}' not found")
                    continue
                self.patient_uuid_by_patient_id[pid] = pat_uuid

            # Resolve doctor UUID
            doc_name = row[doc_name_idx].strip() if doc_name_idx is not None and doc_name_idx < len(row) else ""
            stmt = select(Doctor.id).where(Doctor.tenant_id == self.tenant_id)
            if doc_name:
                stmt = stmt.where(Doctor.name.ilike(f"%{doc_name}%"))
            doc_uuid = self.session.execute(stmt).scalars().first()

            if not doc_uuid:
                # Fallback to any doctor in tenant
                doc_uuid = self.session.execute(select(Doctor.id).where(Doctor.tenant_id == self.tenant_id)).scalars().first()

            if not doc_uuid:
                self.report.add_error("appointments", token_no, "No doctors available in tenant")
                continue

            app_date = row[date_idx].strip() if date_idx is not None and date_idx < len(row) else "2026-10-01"
            app_time = row[time_idx].strip() if time_idx is not None and time_idx < len(row) else "10:00 AM"
            amount = row[amt_idx].strip() if amt_idx is not None and amt_idx < len(row) else "500"
            pay_m = row[pay_method_idx].strip() if pay_method_idx is not None and pay_method_idx < len(row) else "Offline"
            pay_s = row[pay_status_idx].strip() if pay_status_idx is not None and pay_status_idx < len(row) else "Pending"
            book_s = row[book_status_idx].strip() if book_status_idx is not None and book_status_idx < len(row) else "Confirmed"

            stmt = select(Appointment).where(
                Appointment.tenant_id == self.tenant_id,
                Appointment.token_no == token_no,
            )
            existing = self.session.execute(stmt).scalar_one_or_none()

            # Prevent uq_appointment_doctor_datetime collision
            conflict_stmt = select(Appointment).where(
                Appointment.doctor_id == doc_uuid,
                Appointment.appointment_date == app_date,
                Appointment.appointment_time == app_time,
            )
            conflict = self.session.execute(conflict_stmt).scalar_one_or_none()
            if conflict and (not existing or conflict.id != existing.id):
                self.report.record_action("duplicates", "appointments")
                self.report.add_warning(
                    f"Slot collision for Doctor {doc_uuid} on {app_date} {app_time}: "
                    f"token {token_no} collides with {conflict.token_no}. "
                    "Disambiguating appointment_time to preserve record."
                )
                app_time = f"{app_time}+1"

            # Resolve slot_id if available
            slot_stmt = select(AppointmentSlot.id).where(
                AppointmentSlot.tenant_id == self.tenant_id,
                AppointmentSlot.doctor_id == doc_uuid,
                AppointmentSlot.date == app_date,
                AppointmentSlot.start_time == app_time,
            )
            slot_uuid = self.session.execute(slot_stmt).scalar_one_or_none()

            if existing:
                existing.payment_status = pay_s
                existing.booking_status = book_s
                existing.slot_id = slot_uuid or existing.slot_id
                self.appointment_uuid_by_token[token_no] = existing.id
                self.report.record_action("appointments", "updated")
            else:
                app = Appointment(
                    tenant_id=self.tenant_id,
                    token_no=token_no,
                    patient_id=pat_uuid,
                    doctor_id=doc_uuid,
                    slot_id=slot_uuid,
                    appointment_date=app_date,
                    appointment_time=app_time,
                    amount=amount,
                    payment_method=pay_m,
                    payment_status=pay_s,
                    booking_status=book_s,
                )
                self.session.add(app)
                self.session.flush()
                self.appointment_uuid_by_token[token_no] = app.id
                self.report.record_action("appointments", "created")

    def migrate_invoices_and_payments(self):
        """Generate Invoice and Payment records corresponding to migrated appointments."""
        stmt = select(Appointment).where(Appointment.tenant_id == self.tenant_id)
        appointments = self.session.execute(stmt).scalars().all()
        self.report.entity_counts["invoices"]["source"] = len(appointments)
        self.report.entity_counts["payments"]["source"] = len(appointments)

        for app in appointments:
            inv_no = f"INV-{app.token_no}"
            inv_stmt = select(Invoice).where(
                Invoice.tenant_id == self.tenant_id,
                Invoice.invoice_number == inv_no,
            )
            existing_inv = self.session.execute(inv_stmt).scalar_one_or_none()
            if existing_inv:
                existing_inv.payment_status = app.payment_status
                existing_inv.amount = app.amount
                self.report.record_action("invoices", "updated")
                inv_obj = existing_inv
            else:
                inv_obj = Invoice(
                    tenant_id=self.tenant_id,
                    invoice_number=inv_no,
                    appointment_id=app.id,
                    patient_id=app.patient_id,
                    amount=app.amount,
                    payment_method=app.payment_method or "Offline",
                    payment_status=app.payment_status or "Pending",
                    issued_date=app.appointment_date,
                )
                self.session.add(inv_obj)
                self.session.flush()
                self.report.record_action("invoices", "created")

            # Payment
            pay_id = f"PAY-{app.token_no}"
            pay_stmt = select(Payment).where(
                Payment.tenant_id == self.tenant_id,
                Payment.payment_id == pay_id,
            )
            existing_pay = self.session.execute(pay_stmt).scalar_one_or_none()
            if existing_pay:
                existing_pay.payment_status = app.payment_status
                existing_pay.amount = app.amount
                self.report.record_action("payments", "updated")
            else:
                pay_obj = Payment(
                    tenant_id=self.tenant_id,
                    payment_id=pay_id,
                    appointment_id=app.id,
                    invoice_id=inv_obj.id,
                    amount=app.amount,
                    currency="INR",
                    payment_method=app.payment_method or "Offline",
                    payment_status=app.payment_status or "Pending",
                    gateway="Offline",
                )
                self.session.add(pay_obj)
                self.session.flush()
                self.report.record_action("payments", "created")

    def migrate_prescriptions(self, rx_data: Optional[Dict[str, Any]] = None):
        """Migrate digital prescriptions and nested medicines."""
        data = rx_data
        if data is None:
            path = self.data_dir / "prescriptions.json"
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    self.report.add_warning(f"Could not load prescriptions.json: {e}")
                    data = {}
            else:
                data = {}

        if not data:
            return

        self.report.entity_counts["prescriptions"]["source"] = len(data)

        for rx_id, r in data.items():
            pid = r.get("patient_id", "")
            doc_id = r.get("doctor_id", "")
            app_id = r.get("appointment_id", "")

            # Look up or resolve patient UUID
            pat_uuid = self.patient_uuid_by_patient_id.get(pid)
            if not pat_uuid:
                stmt = select(Patient.id).where(Patient.tenant_id == self.tenant_id, Patient.patient_id == pid)
                pat_uuid = self.session.execute(stmt).scalar_one_or_none()
            if not pat_uuid:
                stub_pat = Patient(
                    tenant_id=self.tenant_id,
                    patient_id=pid or f"PAT-{uuid.uuid4().hex[:6]}",
                    name=r.get("patient_name") or "Migrated Patient",
                    phone=r.get("patient_phone") or "0000000000",
                    email=r.get("patient_email") or "",
                )
                self.session.add(stub_pat)
                self.session.flush()
                pat_uuid = stub_pat.id
                self.patient_uuid_by_patient_id[stub_pat.patient_id] = pat_uuid

            # Look up doctor UUID
            doc_uuid = self.doctor_uuid_by_doc_id.get(doc_id)
            if not doc_uuid:
                stmt = select(Doctor.id).where(Doctor.tenant_id == self.tenant_id, Doctor.doctor_id == doc_id)
                doc_uuid = self.session.execute(stmt).scalar_one_or_none()
            if not doc_uuid:
                doc_uuid = self.session.execute(select(Doctor.id).where(Doctor.tenant_id == self.tenant_id)).scalars().first()
            if not doc_uuid:
                stub_doc = Doctor(
                    tenant_id=self.tenant_id,
                    doctor_id=doc_id or "DOC_DEFAULT",
                    name=r.get("doctor_name") or "Consulting Physician",
                    specialization="General",
                )
                self.session.add(stub_doc)
                self.session.flush()
                doc_uuid = stub_doc.id
                self.doctor_uuid_by_doc_id[stub_doc.doctor_id] = doc_uuid

            # Look up appointment UUID if token present
            app_uuid = self.appointment_uuid_by_token.get(app_id)
            if not app_uuid and app_id:
                stmt = select(Appointment.id).where(Appointment.tenant_id == self.tenant_id, Appointment.token_no == app_id)
                app_uuid = self.session.execute(stmt).scalar_one_or_none()

            stmt = select(Prescription).where(
                Prescription.tenant_id == self.tenant_id,
                Prescription.prescription_id == rx_id,
            )
            existing = self.session.execute(stmt).scalar_one_or_none()

            date_str = r.get("date") or r.get("created_at", "")[:10] or "2026-10-01"
            status_str = r.get("status") or "finalized"

            if existing:
                existing.diagnosis = r.get("diagnosis", "")
                existing.symptoms = r.get("symptoms", "")
                existing.advice = r.get("advice", "")
                existing.status = status_str
                rx_obj = existing
                self.report.record_action("prescriptions", "updated")
            else:
                rx_obj = Prescription(
                    tenant_id=self.tenant_id,
                    prescription_id=rx_id,
                    patient_id=pat_uuid,
                    doctor_id=doc_uuid,
                    appointment_id=app_uuid,
                    date=date_str,
                    version=int(r.get("version", 1)),
                    status=status_str,
                    diagnosis=r.get("diagnosis", ""),
                    symptoms=r.get("symptoms", ""),
                    advice=r.get("advice", ""),
                    follow_up_date=r.get("follow_up_date", ""),
                    created_by=r.get("created_by", ""),
                    version_history=r.get("version_history"),
                )
                self.session.add(rx_obj)
                self.session.flush()
                self.report.record_action("prescriptions", "created")

            # Migrate nested items
            medicines = r.get("medicines") or []
            if existing:
                self.session.execute(delete(PrescriptionItem).where(PrescriptionItem.prescription_id == rx_obj.id))
            self.report.entity_counts["prescription_items"]["source"] += len(medicines)
            for idx, med in enumerate(medicines):
                item = PrescriptionItem(
                    prescription_id=rx_obj.id,
                    order_index=idx,
                    name=med.get("name", "Medicine"),
                    dosage=med.get("dosage", ""),
                    frequency=med.get("frequency", ""),
                    duration=med.get("duration", ""),
                    instructions=med.get("instructions", ""),
                )
                self.session.add(item)
                self.report.record_action("prescription_items", "created")

    def migrate_audit_logs(self):
        """Migrate historical audit logs from audit_logs.jsonl into PostgreSQL."""
        path = self.data_dir / "audit_logs.jsonl"
        if not path.exists():
            return

        lines = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.report.add_warning(f"Could not read audit_logs.jsonl: {e}")
            return

        self.report.entity_counts["audit_logs"]["source"] = len(lines)
        batch = 0
        for raw in lines:
            try:
                entry = json.loads(raw)
            except Exception:
                continue

            aid = entry.get("audit_id") or entry.get("id") or str(uuid.uuid4())
            stmt = select(AuditLog.id).where(
                AuditLog.tenant_id == self.tenant_id,
                AuditLog.audit_id == aid,
            )
            if self.session.execute(stmt).scalar_one_or_none():
                self.report.record_action("audit_logs", "skipped")
                continue

            ts_str = entry.get("timestamp")
            dt = None
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except Exception:
                    dt = datetime.now(timezone.utc)
            else:
                dt = datetime.now(timezone.utc)

            log_rec = AuditLog(
                tenant_id=self.tenant_id,
                audit_id=aid,
                timestamp=dt,
                user=entry.get("user") or entry.get("username") or "system",
                action=entry.get("action") or "UNKNOWN",
                entity_type=entry.get("entity_type") or "system",
                entity_id=entry.get("entity_id") or "0",
                details=entry.get("details"),
                ip_address=entry.get("ip_address"),
                user_agent=entry.get("user_agent"),
            )
            self.session.add(log_rec)
            batch += 1
            if batch % 100 == 0:
                self.session.flush()
            self.report.record_action("audit_logs", "created")

        if batch % 100 != 0:
            self.session.flush()

    def _load_sheet_rows_from_cache(self, entity_type: str) -> List[List[str]]:
        """Load sheet rows from live Google Sheets API or fall back to cached backup snapshots."""
        try:
            settings = get_settings()
            if settings.clinic_sheet_id:
                sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
                from sheet_tools import read_sheet
                range_map = {
                    "doctors": settings.clinic_sheet_range,
                    "patients": settings.patient_sheet_range,
                    "slots": settings.appointment_slot_sheet_range,
                }
                target_range = range_map.get(entity_type)
                if target_range:
                    rows = read_sheet.invoke({
                        "spreadsheet_id": settings.clinic_sheet_id,
                        "range_name": target_range,
                    })
                    if rows and len(rows) > 0:
                        logger.info(f"Loaded {len(rows)} live rows from Google Sheets for {entity_type}")
                        return rows
        except Exception as e:
            logger.debug(f"Live Google Sheets read for {entity_type} skipped: {e}")

        # Fall back to snapshot
        snapshot_file = self.data_dir / "backup_pre_postgres_migration" / f"google_sheets_{entity_type}.json"
        if snapshot_file.exists():
            try:
                with open(snapshot_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        logger.info(f"Loaded {len(data)} rows from backup snapshot for {entity_type}")
                        return data
            except Exception as e:
                self.report.add_warning(f"Failed to load snapshot for {entity_type}: {e}")

        return []


def main():
    parser = argparse.ArgumentParser(description="Migrate Google Sheets & JSON data into PostgreSQL.")
    parser.add_argument("--tenant-id", default="default", help="Target clinic tenant ID (default: 'default')")
    parser.add_argument("--clinic-name", default="XYZ Clinic", help="Clinic facility name")
    parser.add_argument("--commit", action="store_true", help="Commit changes (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Simulate migration without committing")
    parser.add_argument("--database-url", default=None, help="Optional database URL override")
    parser.add_argument("--report-out", default=None, help="Path to save JSON reconciliation report")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    is_dry_run = not args.commit or args.dry_run

    print("=" * 70)
    print(" CLINIC MULTI-TENANT DATABASE MIGRATION ENGINE")
    print(f" Target Tenant: {args.tenant_id} ({args.clinic_name})")
    print(f" Mode:          {'DRY RUN (Simulated, no changes written)' if is_dry_run else 'LIVE COMMIT'}")
    print("=" * 70)

    try:
        session_factory = get_session_factory(args.database_url)
    except Exception as e:
        print(f"FATAL: Database connection failed: {e}")
        sys.exit(1)

    with session_factory() as session:
        migrator = DataMigrator(
            session=session,
            tenant_id=args.tenant_id,
            clinic_name=args.clinic_name,
            dry_run=is_dry_run,
        )
        report = migrator.run(
            include_admin_users=True,
            include_invoices_and_payments=True,
            include_audit_logs=True,
        )

    print("\n--- MIGRATION RECONCILIATION SUMMARY ---")
    for entity, counts in report["entity_counts"].items():
        if isinstance(counts, dict) and "source" in counts:
            print(f"  {entity.ljust(20)}: Source={counts['source']} | Created={counts['created']} | Updated={counts['updated']} | Skipped={counts['skipped']}")
        else:
            print(f"  {entity.ljust(20)}: {counts}")

    print(f"\nTotal Errors:   {report['errors_count']}")
    print(f"Total Warnings: {report['warnings_count']}")

    if not is_dry_run and report.get("final_database_counts"):
        print("\n--- FINAL POSTGRESQL TABLE COUNTS ---")
        for tbl, cnt in sorted(report["final_database_counts"].items()):
            print(f"  {tbl.ljust(22)}: {cnt} rows")

    if args.report_out:
        out_path = Path(args.report_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed reconciliation report saved to: {out_path}")

    print("=" * 70)


if __name__ == "__main__":
    main()
