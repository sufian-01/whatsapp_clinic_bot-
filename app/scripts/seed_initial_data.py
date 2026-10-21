"""Seed initial/backup clinic data into PostgreSQL if empty.

Ensures:
1. Default clinic tenant ('default') exists in clinics table.
2. If doctors table is empty, restores existing backup records from data/backup_pre_operational_cutover:
   - clinics
   - users
   - doctors
   - patients
   - appointment_slots
   - appointments
   - invoices
   - payments
   - prescriptions
   - prescription_items
3. Admin and Super Admin accounts exist and match configured environment passwords.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import func, select
from app.core.auth import hash_password
from app.core.config import get_settings
from app.db.models import (
    Appointment,
    AppointmentSlot,
    Clinic,
    Doctor,
    Invoice,
    Patient,
    Payment,
    Prescription,
    PrescriptionItem,
    User,
)
from app.db.session import get_session_factory, is_db_configured

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed")


def parse_dt(val):
    if not val:
        return datetime.now(timezone.utc)
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return datetime.now(timezone.utc)


def seed_database():
    if not is_db_configured():
        logger.info("[SEED] Database not configured; skipping seed.")
        return

    session_factory = get_session_factory()
    settings = get_settings()

    backup_dir = PROJECT_ROOT / "data" / "backup_pre_operational_cutover"
    if not backup_dir.exists():
        logger.warning("[SEED] Backup directory %s does not exist; skipping restore.", backup_dir)

    with session_factory() as session:
        # 1. Check if default clinic exists
        default_clinic = session.execute(
            select(Clinic).where(Clinic.id == "default")
        ).scalar_one_or_none()

        if not default_clinic:
            logger.info("[SEED] Default clinic ('default') missing in database. Seeding...")
            clinic_file = backup_dir / "clinics.json"
            if clinic_file.exists():
                with open(clinic_file, "r", encoding="utf-8") as f:
                    clinics_data = json.load(f)
                for c in clinics_data:
                    cid = c.get("id", "default")
                    existing = session.execute(select(Clinic).where(Clinic.id == cid)).scalar_one_or_none()
                    if not existing:
                        clinic_obj = Clinic(
                            id=cid,
                            name=c.get("name", settings.clinic_name or "XYZ Clinic"),
                            legal_name=c.get("legal_name", settings.clinic_name or "XYZ Clinic"),
                            logo=c.get("logo"),
                            phone=c.get("phone", settings.support_phone or None),
                            email=c.get("email"),
                            website=c.get("website"),
                            address=c.get("address"),
                            timezone=c.get("timezone", settings.clinic_timezone or "Asia/Kolkata"),
                            currency=c.get("currency", "INR"),
                            upi_id=c.get("upi_id", settings.clinic_upi_id or None),
                            status=c.get("status", "ACTIVE"),
                            is_active=bool(c.get("is_active", True)),
                            working_days=c.get("working_days", "Monday - Friday"),
                            working_hours=c.get("working_hours", "09:00 - 17:00"),
                            appointment_duration=c.get("appointment_duration", 30),
                            booking_settings=c.get("booking_settings"),
                            rag_config_status=c.get("rag_config_status", "CONFIGURED"),
                            channel_config_status=c.get("channel_config_status", "CONFIGURED"),
                            created_at=parse_dt(c.get("created_at")),
                            updated_at=parse_dt(c.get("updated_at")),
                        )
                        session.add(clinic_obj)
            else:
                session.add(
                    Clinic(
                        id="default",
                        name=settings.clinic_name or "XYZ Clinic",
                        legal_name=settings.clinic_name or "XYZ Clinic",
                        status="ACTIVE",
                        is_active=True,
                        timezone=settings.clinic_timezone or "Asia/Kolkata",
                        currency="INR",
                        working_days="Monday - Friday",
                        working_hours="09:00 - 17:00",
                        appointment_duration=30,
                        rag_config_status="CONFIGURED",
                        channel_config_status="CONFIGURED",
                    )
                )
            session.flush()
            logger.info("[SEED] Clinic 'default' created successfully.")

        # 2. Check if doctors table has data
        doc_count = session.execute(select(func.count(Doctor.id))).scalar() or 0
        if doc_count == 0 and (backup_dir / "doctors.json").exists():
            logger.info("[SEED] Database has 0 doctors. Restoring initial dataset from backup...")

            # 2a. Users
            users_file = backup_dir / "users.json"
            if users_file.exists():
                with open(users_file, "r", encoding="utf-8") as f:
                    users_data = json.load(f)
                for u in users_data:
                    uid = u.get("id")
                    if not session.execute(select(User).where(User.id == uid)).scalar_one_or_none():
                        session.add(
                            User(
                                id=uid,
                                tenant_id=u.get("tenant_id", "default"),
                                username=u.get("username"),
                                password_hash=u.get("password_hash"),
                                role=u.get("role", "doctor"),
                                doctor_id=u.get("doctor_id"),
                                full_name=u.get("full_name"),
                                email=u.get("email"),
                                phone=u.get("phone"),
                                status=u.get("status", "Active"),
                                must_change_password=bool(u.get("must_change_password", False)),
                                last_login=parse_dt(u.get("last_login")) if u.get("last_login") else None,
                                created_at=parse_dt(u.get("created_at")),
                                updated_at=parse_dt(u.get("updated_at")),
                            )
                        )
                session.flush()

            # 2b. Doctors
            doctors_file = backup_dir / "doctors.json"
            if doctors_file.exists():
                with open(doctors_file, "r", encoding="utf-8") as f:
                    doctors_data = json.load(f)
                for d in doctors_data:
                    did = d.get("id")
                    if not session.execute(select(Doctor).where(Doctor.id == did)).scalar_one_or_none():
                        session.add(
                            Doctor(
                                id=did,
                                tenant_id=d.get("tenant_id", "default"),
                                doctor_id=d.get("doctor_id"),
                                name=d.get("name"),
                                specialization=d.get("specialization"),
                                qualification=d.get("qualification"),
                                registration_no=d.get("registration_no"),
                                phone=d.get("phone"),
                                email=d.get("email"),
                                available_days=d.get("available_days"),
                                start_time=d.get("start_time"),
                                end_time=d.get("end_time"),
                                consultation_fee=str(d.get("consultation_fee", "500")),
                                photo=d.get("photo"),
                                signature=d.get("signature"),
                                bio=d.get("bio"),
                                status=d.get("status", "Active"),
                                created_at=parse_dt(d.get("created_at")),
                                updated_at=parse_dt(d.get("updated_at")),
                            )
                        )
                session.flush()

            # 2c. Patients
            patients_file = backup_dir / "patients.json"
            if patients_file.exists():
                with open(patients_file, "r", encoding="utf-8") as f:
                    patients_data = json.load(f)
                for p in patients_data:
                    pid = p.get("id")
                    if not session.execute(select(Patient).where(Patient.id == pid)).scalar_one_or_none():
                        session.add(
                            Patient(
                                id=pid,
                                tenant_id=p.get("tenant_id", "default"),
                                patient_id=p.get("patient_id"),
                                name=p.get("name"),
                                phone=p.get("phone"),
                                email=p.get("email"),
                                age=str(p.get("age")) if p.get("age") is not None else None,
                                gender=p.get("gender"),
                                address=p.get("address"),
                                medical_history=p.get("medical_history"),
                                status=p.get("status", "Active"),
                                created_at=parse_dt(p.get("created_at")),
                                updated_at=parse_dt(p.get("updated_at")),
                            )
                        )
                session.flush()

            # 2d. Appointment Slots
            slots_file = backup_dir / "appointment_slots.json"
            if slots_file.exists():
                with open(slots_file, "r", encoding="utf-8") as f:
                    slots_data = json.load(f)
                for s in slots_data:
                    sid = s.get("id")
                    if not session.execute(select(AppointmentSlot).where(AppointmentSlot.id == sid)).scalar_one_or_none():
                        session.add(
                            AppointmentSlot(
                                id=sid,
                                tenant_id=s.get("tenant_id", "default"),
                                slot_id=s.get("slot_id"),
                                doctor_id=s.get("doctor_id"),
                                date=s.get("date"),
                                start_time=s.get("start_time"),
                                end_time=s.get("end_time"),
                                status=s.get("status", "available"),
                                locked_by=s.get("locked_by"),
                                locked_at=parse_dt(s.get("locked_at")) if s.get("locked_at") else None,
                                booked_patient_id=s.get("booked_patient_id"),
                                booked_token_no=s.get("booked_token_no"),
                                created_at=parse_dt(s.get("created_at")),
                                updated_at=parse_dt(s.get("updated_at")),
                            )
                        )
                session.flush()

            # 2e. Appointments
            appts_file = backup_dir / "appointments.json"
            if appts_file.exists():
                with open(appts_file, "r", encoding="utf-8") as f:
                    appts_data = json.load(f)
                for a in appts_data:
                    aid = a.get("id")
                    if not session.execute(select(Appointment).where(Appointment.id == aid)).scalar_one_or_none():
                        session.add(
                            Appointment(
                                id=aid,
                                tenant_id=a.get("tenant_id", "default"),
                                token_no=a.get("token_no"),
                                patient_id=a.get("patient_id"),
                                doctor_id=a.get("doctor_id"),
                                slot_id=a.get("slot_id"),
                                appointment_date=a.get("appointment_date"),
                                appointment_time=a.get("appointment_time"),
                                amount=str(a.get("amount", "500")),
                                payment_method=a.get("payment_method", "Offline"),
                                payment_status=a.get("payment_status", "Pending"),
                                booking_status=a.get("booking_status", "Confirmed"),
                                notes=a.get("notes"),
                                created_at=parse_dt(a.get("created_at")),
                                updated_at=parse_dt(a.get("updated_at")),
                            )
                        )
                session.flush()

            # 2f. Invoices & Payments
            invoices_file = backup_dir / "invoices.json"
            if invoices_file.exists():
                with open(invoices_file, "r", encoding="utf-8") as f:
                    invoices_data = json.load(f)
                for inv in invoices_data:
                    invid = inv.get("id")
                    if not session.execute(select(Invoice).where(Invoice.id == invid)).scalar_one_or_none():
                        session.add(
                            Invoice(
                                id=invid,
                                tenant_id=inv.get("tenant_id", "default"),
                                invoice_number=inv.get("invoice_number"),
                                appointment_id=inv.get("appointment_id"),
                                patient_id=inv.get("patient_id"),
                                amount=str(inv.get("amount", "500")),
                                payment_method=inv.get("payment_method", "Cash"),
                                payment_status=inv.get("payment_status", "Pending"),
                                upi_id=inv.get("upi_id"),
                                qr_path=inv.get("qr_path"),
                                pdf_path=inv.get("pdf_path"),
                                issued_date=inv.get("issued_date"),
                                notes=inv.get("notes"),
                                created_at=parse_dt(inv.get("created_at")),
                                updated_at=parse_dt(inv.get("updated_at")),
                            )
                        )
                session.flush()

            payments_file = backup_dir / "payments.json"
            if payments_file.exists():
                with open(payments_file, "r", encoding="utf-8") as f:
                    payments_data = json.load(f)
                for pay in payments_data:
                    payid = pay.get("id")
                    if not session.execute(select(Payment).where(Payment.id == payid)).scalar_one_or_none():
                        session.add(
                            Payment(
                                id=payid,
                                tenant_id=pay.get("tenant_id", "default"),
                                payment_id=pay.get("payment_id"),
                                appointment_id=pay.get("appointment_id"),
                                invoice_id=pay.get("invoice_id"),
                                amount=str(pay.get("amount", "500")),
                                currency=pay.get("currency", "INR"),
                                payment_method=pay.get("payment_method", "Cash"),
                                payment_status=pay.get("payment_status", "Pending"),
                                transaction_reference=pay.get("transaction_reference"),
                                gateway=pay.get("gateway", "Manual"),
                                gateway_payload=pay.get("gateway_payload"),
                                paid_at=parse_dt(pay.get("paid_at")) if pay.get("paid_at") else None,
                                created_at=parse_dt(pay.get("created_at")),
                                updated_at=parse_dt(pay.get("updated_at")),
                            )
                        )
                session.flush()

            # 2g. Prescriptions & Prescription Items
            rx_file = backup_dir / "prescriptions.json"
            if rx_file.exists():
                with open(rx_file, "r", encoding="utf-8") as f:
                    rx_data = json.load(f)
                for rx in rx_data:
                    rxid = rx.get("id")
                    if not session.execute(select(Prescription).where(Prescription.id == rxid)).scalar_one_or_none():
                        session.add(
                            Prescription(
                                id=rxid,
                                tenant_id=rx.get("tenant_id", "default"),
                                prescription_id=rx.get("prescription_id"),
                                patient_id=rx.get("patient_id"),
                                doctor_id=rx.get("doctor_id"),
                                appointment_id=rx.get("appointment_id"),
                                date=rx.get("date"),
                                version=rx.get("version", 1),
                                status=rx.get("status", "draft"),
                                chief_complaints=rx.get("chief_complaints"),
                                diagnosis=rx.get("diagnosis"),
                                symptoms=rx.get("symptoms"),
                                vitals=rx.get("vitals"),
                                clinical_notes=rx.get("clinical_notes"),
                                tests_advised=rx.get("tests_advised"),
                                advice=rx.get("advice"),
                                follow_up_date=rx.get("follow_up_date"),
                                created_by=rx.get("created_by"),
                                updated_by=rx.get("updated_by"),
                                finalized_at=parse_dt(rx.get("finalized_at")) if rx.get("finalized_at") else None,
                                version_history=rx.get("version_history"),
                                email_delivery=rx.get("email_delivery"),
                                pdf_path=rx.get("pdf_path"),
                                created_at=parse_dt(rx.get("created_at")),
                                updated_at=parse_dt(rx.get("updated_at")),
                            )
                        )
                session.flush()

            items_file = backup_dir / "prescription_items.json"
            if items_file.exists():
                with open(items_file, "r", encoding="utf-8") as f:
                    items_data = json.load(f)
                for it in items_data:
                    itid = it.get("id")
                    if not session.execute(select(PrescriptionItem).where(PrescriptionItem.id == itid)).scalar_one_or_none():
                        session.add(
                            PrescriptionItem(
                                id=itid,
                                prescription_id=it.get("prescription_id"),
                                order_index=it.get("order_index", 0),
                                name=it.get("name"),
                                strength=it.get("strength"),
                                dosage=it.get("dosage"),
                                frequency=it.get("frequency"),
                                duration=it.get("duration"),
                                instructions=it.get("instructions"),
                                created_at=parse_dt(it.get("created_at")),
                                updated_at=parse_dt(it.get("updated_at")),
                            )
                        )
                session.flush()

            logger.info("[SEED] All backup records restored into database successfully.")

        # 3. Ensure Admin & Super Admin password synchronization from environment variables
        admin_pass = os.getenv("CRM_ADMIN_PASSWORD", "").strip()
        if admin_pass:
            admin_user = session.execute(select(User).where(User.username == "admin")).scalar_one_or_none()
            if admin_user:
                admin_user.password_hash = hash_password(admin_pass)
                logger.info("[SEED] Updated admin password from CRM_ADMIN_PASSWORD.")
            else:
                session.add(
                    User(
                        tenant_id="default",
                        username="admin",
                        password_hash=hash_password(admin_pass),
                        role="TENANT_ADMIN",
                        full_name="Clinic Administrator",
                        status="Active",
                        must_change_password=False,
                    )
                )

        super_pass = os.getenv("SUPER_ADMIN_PASSWORD", "").strip()
        if super_pass:
            sa_user = session.execute(select(User).where(User.username == "superadmin")).scalar_one_or_none()
            if sa_user:
                sa_user.password_hash = hash_password(super_pass)
                logger.info("[SEED] Updated superadmin password from SUPER_ADMIN_PASSWORD.")
            else:
                session.add(
                    User(
                        tenant_id=None,
                        username="superadmin",
                        password_hash=hash_password(super_pass),
                        role="SUPER_ADMIN",
                        full_name="Platform Super Admin",
                        status="Active",
                        must_change_password=False,
                    )
                )

        session.commit()
        logger.info("[SEED] Database seeding and credential check finished successfully.")


if __name__ == "__main__":
    seed_database()
