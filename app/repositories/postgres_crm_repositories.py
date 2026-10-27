"""PostgreSQL-backed repositories for CRM, Doctor Portal, and Chatbot workflows.

Replaces Google Sheets and JSON flat files with direct PostgreSQL persistence,
enforcing strict multi-tenant isolation, atomic transaction commits, and
deterministic dictionary interfaces for seamless compatibility.
"""

from datetime import datetime, timezone
from difflib import SequenceMatcher
from decimal import Decimal, InvalidOperation
import math
from pathlib import Path
import re
from threading import RLock
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode
from uuid import uuid4

import qrcode
from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.orm import Session, sessionmaker

from ..core.auth import hash_password, verify_password
from ..core.tenant import get_current_tenant
from ..db.models import (
    Appointment,
    AppointmentSlot,
    AuditLog,
    Clinic,
    Contact,
    Doctor,
    Invoice,
    Patient,
    Payment,
    Prescription,
    PrescriptionItem,
    User,
)
from ..tools.doctors import _HEALTH_CONCERN_MAP, _SPECIALIZATION_ALIASES
from ..tools.patients import PatientRecord
from ..tools.prescription_pdf import PrescriptionPDFData, generate_prescription_pdf


def _resolve_tenant_id() -> str:
    """Resolve active tenant_id from request context or default."""
    ctx = get_current_tenant()
    if ctx and ctx.tenant_id and ctx.tenant_id.strip() and ctx.tenant_id != "platform":
        return ctx.tenant_id.strip()
    return "default"


# ---------------------------------------------------------------------------
# 1. PostgreSQL Patient Repository
# ---------------------------------------------------------------------------

class PostgresPatientRepository:
    """PostgreSQL-backed patient & booking repository."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self._lock = RLock()

    def invalidate_cache(self) -> None:
        """Cache invalidation hook (PostgreSQL is live, no stale cache)."""
        pass

    def list_records(self) -> List[Dict[str, str]]:
        """List patient booking records for the active tenant."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            # Query appointments joined with patients and doctors
            stmt = (
                select(Appointment, Patient, Doctor)
                .join(Patient, Appointment.patient_id == Patient.id)
                .outerjoin(Doctor, Appointment.doctor_id == Doctor.id)
                .where(Appointment.tenant_id == tenant_id)
                .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
            )
            rows = session.execute(stmt).all()

            records = []
            seen_patient_ids = set()
            for appt, patient, doctor in rows:
                seen_patient_ids.add(patient.patient_id)
                rec = {
                    "Patient ID": patient.patient_id,
                    "Name": patient.name,
                    "Phone": patient.phone,
                    "Email": patient.email or "",
                    "Age": str(patient.age or ""),
                    "Gender": patient.gender or "",
                    "Doctor": doctor.name if doctor else "",
                    "Appointment Date": appt.appointment_date,
                    "Appointment Time": appt.appointment_time,
                    "Status": appt.booking_status,
                    "Token No": appt.token_no,
                    "Amount": str(appt.amount or "500"),
                    "Payment Method": appt.payment_method or "Offline",
                    "Payment Status": appt.payment_status or "Pending",
                    "Booking Status": appt.booking_status or "Confirmed",
                    "Created At": appt.created_at.isoformat() if appt.created_at else "",
                }
                records.append(rec)

            # Also include patients who do not have an active appointment yet
            unbooked_stmt = (
                select(Patient)
                .where(
                    Patient.tenant_id == tenant_id,
                    ~Patient.patient_id.in_(seen_patient_ids) if seen_patient_ids else True,
                )
                .order_by(Patient.name)
            )
            unbooked = session.execute(unbooked_stmt).scalars().all()
            for p in unbooked:
                records.append({
                    "Patient ID": p.patient_id,
                    "Name": p.name,
                    "Phone": p.phone,
                    "Email": p.email or "",
                    "Age": str(p.age or ""),
                    "Gender": p.gender or "",
                    "Doctor": "",
                    "Appointment Date": "",
                    "Appointment Time": "",
                    "Status": getattr(p, "status", "Active"),
                    "Token No": "",
                    "Amount": "",
                    "Payment Method": "",
                    "Payment Status": "",
                    "Booking Status": "",
                    "Created At": p.created_at.isoformat() if p.created_at else "",
                })

            return records

    def list_patients(self) -> List[Dict[str, str]]:
        """Tool facade alias for list_records."""
        return self.list_records()

    def create_patient(self, patient: PatientRecord) -> Dict[str, str]:
        """Create or update patient and associated appointment, invoice, and payment in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            try:
                # 1. Resolve or create Contact
                phone_clean = patient.phone.strip() if patient.phone else ""
                contact_row = None
                if phone_clean:
                    contact_row = session.execute(
                        select(Contact).where(
                            Contact.tenant_id == tenant_id,
                            Contact.phone == phone_clean,
                        )
                    ).scalar_one_or_none()
                    if not contact_row:
                        contact_row = Contact(
                            tenant_id=tenant_id,
                            phone=phone_clean,
                            full_name=patient.name.strip() if patient.name else None,
                        )
                        session.add(contact_row)
                        session.flush()

                # 2. Resolve or create Patient
                pat_row = None
                if patient.patient_id:
                    pat_row = session.execute(
                        select(Patient).where(
                            Patient.tenant_id == tenant_id,
                            Patient.patient_id == patient.patient_id.strip(),
                        )
                    ).scalar_one_or_none()

                rel_type = getattr(patient, "relationship_type", "Self") or "Self"
                dob = getattr(patient, "date_of_birth", None)

                if not pat_row:
                    pid = patient.patient_id or f"PAT-{uuid4().hex[:12].upper()}"
                    pat_row = Patient(
                        tenant_id=tenant_id,
                        patient_id=pid,
                        contact_id=contact_row.id if contact_row else None,
                        relationship_type=rel_type,
                        date_of_birth=dob,
                        name=patient.name.strip(),
                        phone=patient.phone.strip(),
                        email=patient.email.strip() if patient.email else None,
                        age=str(patient.age).strip() if patient.age else None,
                        gender=patient.gender.strip() if patient.gender else None,
                        status="Active",
                    )
                    session.add(pat_row)
                    session.flush()
                else:
                    if contact_row and not pat_row.contact_id:
                        pat_row.contact_id = contact_row.id
                    if rel_type and rel_type != "Self":
                        pat_row.relationship_type = rel_type
                    if dob:
                        pat_row.date_of_birth = dob
                    # Update fields if provided
                    if patient.name: pat_row.name = patient.name.strip()
                    if patient.phone: pat_row.phone = patient.phone.strip()
                    if patient.email: pat_row.email = patient.email.strip()
                    if patient.age: pat_row.age = str(patient.age).strip()
                    if patient.gender: pat_row.gender = patient.gender.strip()
                    session.flush()

                # 2. Resolve Doctor if appointment details provided
                doc_row = None
                if patient.doctor:
                    doc_row = session.execute(
                        select(Doctor).where(
                            Doctor.tenant_id == tenant_id,
                            or_(
                                Doctor.name.ilike(patient.doctor.strip()),
                                Doctor.doctor_id == patient.doctor.strip(),
                            ),
                        )
                    ).scalars().first()

                # 3. Create Appointment if token or date provided
                token_no = patient.token_no
                if not token_no and (patient.appointment_date or patient.doctor):
                    token_no = self.next_token()

                if token_no and doc_row:
                    # Resolve slot if available
                    slot_id = None
                    if patient.appointment_date and patient.appointment_time:
                        slot_row = session.execute(
                            select(AppointmentSlot).where(
                                AppointmentSlot.tenant_id == tenant_id,
                                AppointmentSlot.doctor_id == doc_row.id,
                                AppointmentSlot.date == patient.appointment_date,
                                AppointmentSlot.start_time == patient.appointment_time,
                            )
                        ).scalars().first()
                        if slot_row:
                            slot_id = slot_row.id
                            slot_row.status = "booked"
                            slot_row.booked_patient_id = pat_row.patient_id
                            slot_row.booked_token_no = token_no

                    appt_row = Appointment(
                        tenant_id=tenant_id,
                        token_no=token_no,
                        patient_id=pat_row.id,
                        doctor_id=doc_row.id,
                        slot_id=slot_id,
                        appointment_date=patient.appointment_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        appointment_time=patient.appointment_time or "10:00 AM",
                        amount=str(patient.amount or "500"),
                        payment_method=patient.payment_method or "Offline",
                        payment_status=patient.payment_status or "Pending",
                        booking_status=patient.booking_status or "Confirmed",
                    )
                    session.add(appt_row)
                    session.flush()

                    # 4. Create Invoice and Payment tracking records in PostgreSQL
                    inv_row = Invoice(
                        tenant_id=tenant_id,
                        invoice_number=f"INV-{uuid4().hex[:12].upper()}",
                        appointment_id=appt_row.id,
                        patient_id=pat_row.id,
                        amount=str(patient.amount or "500"),
                        payment_method=patient.payment_method or "Offline",
                        payment_status=patient.payment_status or "Pending",
                        issued_date=appt_row.appointment_date,
                    )
                    session.add(inv_row)
                    session.flush()

                    pay_row = Payment(
                        tenant_id=tenant_id,
                        payment_id=f"PAY-{uuid4().hex[:12].upper()}",
                        appointment_id=appt_row.id,
                        invoice_id=inv_row.id,
                        amount=str(patient.amount or "500"),
                        currency="INR",
                        payment_method=patient.payment_method or "Offline",
                        payment_status=patient.payment_status or "Pending",
                    )
                    session.add(pay_row)

                session.commit()

                return {
                    "Patient ID": pat_row.patient_id,
                    "Name": pat_row.name,
                    "Phone": pat_row.phone,
                    "Email": pat_row.email or "",
                    "Age": str(pat_row.age or ""),
                    "Gender": pat_row.gender or "",
                    "Doctor": doc_row.name if doc_row else patient.doctor,
                    "Appointment Date": patient.appointment_date,
                    "Appointment Time": patient.appointment_time,
                    "Status": patient.booking_status or "Confirmed",
                    "Token No": token_no or "",
                    "Amount": str(patient.amount or "500"),
                    "Payment Method": patient.payment_method or "Offline",
                    "Payment Status": patient.payment_status or "Pending",
                    "Booking Status": patient.booking_status or "Confirmed",
                    "Created At": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as e:
                session.rollback()
                raise e

    def find_by_patient_id(self, patient_id: str) -> Optional[Dict[str, str]]:
        """Look up patient by patient_id in PostgreSQL."""
        records = self.list_records()
        norm = patient_id.strip().casefold()
        for r in records:
            if r.get("Patient ID", "").strip().casefold() == norm:
                return r
        return None

    def find_patient_by_id(self, patient_id: str) -> Dict[str, Any]:
        """Facade method returning dict format."""
        rec = self.find_by_patient_id(patient_id)
        return {"success": bool(rec), "patient": rec}

    def find_by_phone(self, phone: str) -> List[Dict[str, str]]:
        """Find patients matching phone in PostgreSQL."""
        records = self.list_records()
        q = phone.strip()
        return [r for r in records if r.get("Phone", "").strip() == q]

    def find_patient_by_phone(self, phone: str) -> Dict[str, Any]:
        """Facade method returning dict format."""
        recs = self.find_by_phone(phone)
        return {"success": True, "patients": recs}

    def search_by_phone(self, phone: str) -> List[Dict[str, str]]:
        """Alias for find_by_phone."""
        return self.find_by_phone(phone)

    def get_family_members(self, phone: str, tenant_id: Optional[str] = None) -> List[Dict[str, str]]:
        """List all family members associated with a contact phone number."""
        t_id = tenant_id or _resolve_tenant_id()
        clean_phone = phone.strip()
        with self.session_factory() as session:
            stmt = (
                select(Patient)
                .where(
                    Patient.tenant_id == t_id,
                    or_(
                        Patient.phone == clean_phone,
                        Patient.contact.has(Contact.phone == clean_phone),
                    ),
                )
                .order_by(Patient.created_at.asc())
            )
            patients = session.execute(stmt).scalars().all()
            members = []
            seen_ids = set()
            for p in patients:
                if p.patient_id in seen_ids:
                    continue
                seen_ids.add(p.patient_id)
                members.append({
                    "Patient ID": p.patient_id,
                    "Name": p.name,
                    "Phone": p.phone,
                    "Email": p.email or "",
                    "Age": str(p.age or ""),
                    "Gender": p.gender or "",
                    "Relationship": p.relationship_type or "Self",
                    "Date of Birth": p.date_of_birth or "",
                })
            return members

    def has_duplicate_appointment(
        self,
        patient_id_or_name: str,
        doctor_name: str,
        appt_date: str,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Check if an active appointment already exists for patient on date with doctor."""
        t_id = tenant_id or _resolve_tenant_id()
        with self.session_factory() as session:
            stmt = (
                select(Appointment)
                .join(Patient, Appointment.patient_id == Patient.id)
                .join(Doctor, Appointment.doctor_id == Doctor.id)
                .where(
                    Appointment.tenant_id == t_id,
                    Appointment.appointment_date == appt_date,
                    Appointment.booking_status.in_(["Confirmed", "Pending"]),
                    or_(
                        Patient.patient_id == patient_id_or_name,
                        Patient.name.ilike(patient_id_or_name),
                    ),
                    Doctor.name.ilike(f"%{doctor_name}%"),
                )
            )
            return session.execute(stmt).first() is not None

    def find_by_token(self, token_no: str) -> Optional[Dict[str, str]]:
        """Find patient booking matching token_no in PostgreSQL."""
        records = self.list_records()
        norm = token_no.strip().casefold()
        for r in records:
            if r.get("Token No", "").strip().casefold() == norm:
                return r
        return None

    def update_status(self, patient_id: str, status: str) -> bool:
        """Update patient status in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            pat = session.execute(
                select(Patient).where(
                    Patient.tenant_id == tenant_id,
                    Patient.patient_id == patient_id.strip(),
                )
            ).scalar_one_or_none()
            if not pat:
                return False
            pat.status = status.strip()
            session.commit()
            return True

    def update_patient(self, patient_id: str, status: str) -> Dict[str, Any]:
        """Facade method for updating patient status."""
        success = self.update_status(patient_id, status)
        return {"success": success, "patient_id": patient_id, "status": status}

    def update_patient_details(self, patient_id: str, updates: Dict[str, str]) -> bool:
        """Update patient demographic details in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            pat = session.execute(
                select(Patient).where(
                    Patient.tenant_id == tenant_id,
                    Patient.patient_id == patient_id.strip(),
                )
            ).scalar_one_or_none()
            if not pat:
                return False

            key_map = {
                "name": "name", "Name": "name",
                "phone": "phone", "Phone": "phone",
                "email": "email", "Email": "email",
                "age": "age", "Age": "age",
                "gender": "gender", "Gender": "gender",
                "address": "address", "Address": "address",
                "status": "status", "Status": "status",
            }
            for k, v in updates.items():
                attr = key_map.get(k)
                if attr and hasattr(pat, attr):
                    setattr(pat, attr, str(v).strip())

            session.commit()
            return True

    def update_booking_status(self, identifier: str, booking_status: str) -> Dict[str, Any]:
        """Update appointment booking status in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            appt = session.execute(
                select(Appointment).where(
                    Appointment.tenant_id == tenant_id,
                    or_(
                        Appointment.token_no == identifier.strip(),
                        Appointment.id == identifier.strip(),
                    ),
                )
            ).scalar_one_or_none()
            if not appt:
                return {"success": False, "message": f"Appointment '{identifier}' not found"}

            new_status = booking_status.strip().title()
            appt.booking_status = new_status

            # If cancelling appointment, free up the slot
            if new_status.casefold() == "cancelled" and appt.slot_id:
                slot = session.execute(
                    select(AppointmentSlot).where(
                        AppointmentSlot.tenant_id == tenant_id,
                        AppointmentSlot.id == appt.slot_id,
                    )
                ).scalar_one_or_none()
                if slot:
                    slot.status = "available"
                    slot.booked_patient_id = None
                    slot.booked_token_no = None

            session.commit()
            return {"success": True, "token_no": appt.token_no, "status": appt.booking_status}

    def update_payment_status(self, identifier: str, payment_status: str) -> bool:
        """Update payment status in PostgreSQL for appointment, payments, and invoices."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            appt = session.execute(
                select(Appointment).where(
                    Appointment.tenant_id == tenant_id,
                    or_(
                        Appointment.token_no == identifier.strip(),
                        Appointment.id == identifier.strip(),
                    ),
                )
            ).scalar_one_or_none()
            if not appt:
                return False

            formatted = payment_status.strip().title()
            appt.payment_status = formatted

            # Synchronize linked payments and invoices
            pays = session.execute(
                select(Payment).where(Payment.tenant_id == tenant_id, Payment.appointment_id == appt.id)
            ).scalars().all()
            for pay in pays:
                pay.payment_status = formatted
                if formatted.casefold() == "paid":
                    pay.paid_at = datetime.now(timezone.utc)

            invs = session.execute(
                select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.appointment_id == appt.id)
            ).scalars().all()
            for inv in invs:
                inv.payment_status = formatted

            session.commit()
            return True

    def update_appointment_details(self, identifier: str, updates: Dict[str, str]) -> Dict[str, Any]:
        """Update appointment date, time, amount, payment in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            appt = session.execute(
                select(Appointment).where(
                    Appointment.tenant_id == tenant_id,
                    or_(
                        Appointment.token_no == identifier.strip(),
                        Appointment.id == identifier.strip(),
                    ),
                )
            ).scalar_one_or_none()
            if not appt:
                return {"success": False, "message": f"Appointment '{identifier}' not found"}

            if "appointment_date" in updates or "Appointment Date" in updates:
                appt.appointment_date = (updates.get("appointment_date") or updates.get("Appointment Date", "")).strip()
            if "appointment_time" in updates or "Appointment Time" in updates:
                appt.appointment_time = (updates.get("appointment_time") or updates.get("Appointment Time", "")).strip()
            if "slot_id" in updates:
                appt.slot_id = updates["slot_id"].strip()
            if "amount" in updates or "Amount" in updates:
                clean_amt = str(updates.get("amount") or updates.get("Amount", "")).replace("₹", "").replace(",", "").strip()
                appt.amount = clean_amt
            if "notes" in updates:
                appt.notes = updates["notes"].strip()

            if "payment_status" in updates or "Payment Status" in updates:
                new_ps = (updates.get("payment_status") or updates.get("Payment Status", "")).strip().title()
                appt.payment_status = new_ps
                pays = session.execute(
                    select(Payment).where(Payment.tenant_id == tenant_id, Payment.appointment_id == appt.id)
                ).scalars().all()
                for pay in pays:
                    pay.payment_status = new_ps
                    if new_ps.casefold() == "paid":
                        pay.paid_at = datetime.now(timezone.utc)
                invs = session.execute(
                    select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.appointment_id == appt.id)
                ).scalars().all()
                for inv in invs:
                    inv.payment_status = new_ps

            if "payment_method" in updates or "Payment Method" in updates:
                new_pm = (updates.get("payment_method") or updates.get("Payment Method", "")).strip()
                appt.payment_method = new_pm
                pays = session.execute(
                    select(Payment).where(Payment.tenant_id == tenant_id, Payment.appointment_id == appt.id)
                ).scalars().all()
                for pay in pays:
                    pay.payment_method = new_pm

            session.commit()
            return {"success": True, "token_no": appt.token_no}

    def next_token(self) -> str:
        """Generate the next unique token number for the tenant."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            tokens = session.execute(
                select(Appointment.token_no).where(Appointment.tenant_id == tenant_id)
            ).scalars().all()

            used = set()
            for t in tokens:
                if t.startswith("TKN-") and t[4:].isdigit():
                    used.add(int(t[4:]))
            num = 1
            while num in used:
                num += 1
            return f"TKN-{num:04d}"

    def generate_token(self) -> Dict[str, Any]:
        """Facade method for generating token."""
        return {"success": True, "token_no": self.next_token()}

    def new_patient_id(self) -> str:
        """Generate a guaranteed unique patient ID for the tenant."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            for _ in range(10):
                candidate = f"PAT-{uuid4().hex[:12].upper()}"
                exists = session.execute(
                    select(Patient.id).where(
                        Patient.tenant_id == tenant_id,
                        Patient.patient_id == candidate,
                    )
                ).scalar_one_or_none()
                if not exists:
                    return candidate
            return f"PAT-{uuid4().hex[:12].upper()}"

    def generate_patient_id(self) -> Dict[str, Any]:
        """Facade method for generating patient ID."""
        return {"success": True, "patient_id": self.new_patient_id()}


# ---------------------------------------------------------------------------
# 2. PostgreSQL Doctor Directory
# ---------------------------------------------------------------------------

class PostgresDoctorDirectory:
    """PostgreSQL-backed doctor directory with deterministic specialization & fuzzy matching."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self._lock = RLock()

    def invalidate_cache(self) -> None:
        pass

    def get_doctors(self) -> List[Dict[str, str]]:
        """Return all doctor records for the active tenant."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            docs = session.execute(
                select(Doctor).where(Doctor.tenant_id == tenant_id).order_by(Doctor.name)
            ).scalars().all()
            return [self._to_dict(d) for d in docs]

    def get_active_doctors(self) -> List[Dict[str, str]]:
        """Return active doctors for the active tenant."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            docs = session.execute(
                select(Doctor).where(
                    Doctor.tenant_id == tenant_id,
                    Doctor.status == "Active",
                ).order_by(Doctor.name)
            ).scalars().all()
            return [self._to_dict(d) for d in docs]

    def get_doctor_by_id(self, doctor_id: str) -> Optional[Dict[str, str]]:
        """Get doctor by ID or doctor_id in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            doc = session.execute(
                select(Doctor).where(
                    Doctor.tenant_id == tenant_id,
                    or_(Doctor.doctor_id == doctor_id.strip(), Doctor.id == doctor_id.strip()),
                )
            ).scalar_one_or_none()
            return self._to_dict(doc) if doc else None

    def get_doctor_by_name(self, name: str) -> Optional[Dict[str, str]]:
        """Case-insensitive exact name lookup."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            doc = session.execute(
                select(Doctor).where(
                    Doctor.tenant_id == tenant_id,
                    Doctor.name.ilike(name.strip()),
                )
            ).scalars().first()
            return self._to_dict(doc) if doc else None

    def search_doctor(self, name: str) -> Optional[Dict[str, str]]:
        """Facade alias for get_doctor_by_name."""
        return self.get_doctor_by_name(name)

    def get_doctors_by_specialization(self, specialization: str) -> List[Dict[str, str]]:
        """Find doctors by specialization."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            docs = session.execute(
                select(Doctor).where(
                    Doctor.tenant_id == tenant_id,
                    Doctor.specialization.ilike(f"%{specialization.strip()}%"),
                )
            ).scalars().all()
            return [self._to_dict(d) for d in docs]

    def get_doctor_schedule(self, name: str) -> Optional[Dict[str, str]]:
        """Return schedule info for a doctor."""
        doc = self.get_doctor_by_name(name)
        if not doc:
            return None
        return {
            "doctor": doc["Doctor Name"],
            "specialization": doc["Specialization"],
            "available_days": doc["Available Days"],
            "start_time": doc["Start Time"],
            "end_time": doc["End Time"],
        }

    def resolve_doctor(self, text: str) -> Dict[str, Any]:
        """Deterministic resolution by name, alias, or specialization (no LLM required)."""
        active_doctors = self.get_active_doctors()
        if not text or not text.strip():
            return {
                "status": "not_found",
                "doctor": None,
                "matches": [],
                "match_type": "none",
                "matched": None,
                "candidates": [],
            }

        norm_text = text.strip().casefold()

        # 0. Doctor ID direct match (e.g. DOC-001 or doctor:DOC-001)
        raw_upper = text.strip().upper()
        clean_id = raw_upper.removeprefix("DOCTOR:").removeprefix("DOC:").strip()
        for d in active_doctors:
            doc_id = (d.get("Doctor ID") or "").strip().upper()
            if doc_id and doc_id in (raw_upper, clean_id):
                return {
                    "status": "matched",
                    "doctor": d,
                    "matches": [d],
                    "match_type": "doctor",
                    "matched": d,
                    "candidates": [d],
                }

        # 1. Exact or partial doctor name match
        for d in active_doctors:
            doc_name = d["Doctor Name"].casefold()
            clean_name = doc_name.removeprefix("dr.").removeprefix("dr ").strip()
            if norm_text in doc_name or norm_text in clean_name or doc_name in norm_text:
                return {
                    "status": "matched",
                    "doctor": d,
                    "matches": [d],
                    "match_type": "doctor",
                    "matched": d,
                    "candidates": [d],
                }

        # 2. Fuzzy name match
        best_match = None
        best_ratio = 0.0
        for d in active_doctors:
            doc_name = d["Doctor Name"].casefold()
            clean_name = doc_name.removeprefix("dr.").removeprefix("dr ").strip()
            r = max(SequenceMatcher(None, norm_text, doc_name).ratio(), SequenceMatcher(None, norm_text, clean_name).ratio())
            if r > best_ratio and r >= 0.70:
                best_ratio = r
                best_match = d

        if best_match:
            return {
                "status": "matched",
                "doctor": best_match,
                "matches": [best_match],
                "match_type": "doctor",
                "matched": best_match,
                "candidates": [best_match],
            }

        # 3. Specialization match
        for spec_key, aliases in _SPECIALIZATION_ALIASES.items():
            if spec_key in norm_text or any(a in norm_text for a in aliases):
                matching_docs = [d for d in active_doctors if spec_key in d["Specialization"].casefold()]
                if matching_docs:
                    return {
                        "status": "matched" if len(matching_docs) == 1 else "ambiguous",
                        "doctor": matching_docs[0] if len(matching_docs) == 1 else None,
                        "matches": matching_docs,
                        "match_type": "specialization",
                        "matched": matching_docs[0] if len(matching_docs) == 1 else None,
                        "specialization": spec_key.title(),
                        "candidates": matching_docs,
                    }

        # 4. Symptom / Health concern match
        for spec_key, keywords in _HEALTH_CONCERN_MAP.items():
            if any(kw in norm_text for kw in keywords):
                matching_docs = [d for d in active_doctors if spec_key in d["Specialization"].casefold()]
                if matching_docs:
                    return {
                        "status": "matched" if len(matching_docs) == 1 else "ambiguous",
                        "doctor": matching_docs[0] if len(matching_docs) == 1 else None,
                        "matches": matching_docs,
                        "match_type": "health_concern",
                        "matched": matching_docs[0] if len(matching_docs) == 1 else None,
                        "specialization": spec_key.title(),
                        "candidates": matching_docs,
                    }

        return {
            "status": "not_found",
            "doctor": None,
            "matches": [],
            "match_type": "none",
            "matched": None,
            "candidates": [],
        }

    def get_available_doctors_for_date(self, date: str, slot_repository=None) -> List[Dict[str, str]]:
        """Return doctors with open slots on the given date."""
        active = self.get_active_doctors()
        if not slot_repository:
            return active
        available = []
        for d in active:
            slots = slot_repository.get_available_slots(d["Doctor Name"], date)
            if slots:
                available.append(d)
        return available

    def add_doctor(self, data: Dict[str, str]) -> Dict[str, str]:
        """Add new doctor in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            did = data.get("Doctor ID") or data.get("doctor_id") or f"DOC{uuid4().hex[:6].upper()}"
            doc = Doctor(
                tenant_id=tenant_id,
                doctor_id=did,
                name=data.get("Doctor Name") or data.get("name", ""),
                specialization=data.get("Specialization") or data.get("specialization", "General Physician"),
                available_days=data.get("Available Days") or data.get("available_days", "Monday - Friday"),
                start_time=data.get("Start Time") or data.get("start_time", "10:00 AM"),
                end_time=data.get("End Time") or data.get("end_time", "01:00 PM"),
                consultation_fee=str(data.get("Consultation Fee") or data.get("consultation_fee", "500")),
                status=data.get("Status") or data.get("status", "Active"),
                qualification=data.get("Qualification") or data.get("qualification", ""),
                registration_no=data.get("Registration No") or data.get("registration_no", ""),
                phone=data.get("Phone") or data.get("phone", ""),
                email=data.get("Email") or data.get("email", ""),
            )
            session.add(doc)
            session.commit()
            return self._to_dict(doc)

    def update_doctor(self, doctor_id: str, updates: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Update doctor record in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            doc = session.execute(
                select(Doctor).where(
                    Doctor.tenant_id == tenant_id,
                    or_(Doctor.doctor_id == doctor_id.strip(), Doctor.id == doctor_id.strip()),
                )
            ).scalar_one_or_none()
            if not doc:
                return None

            key_map = {
                "name": "name", "Doctor Name": "name",
                "specialization": "specialization", "Specialization": "specialization",
                "available_days": "available_days", "Available Days": "available_days",
                "start_time": "start_time", "Start Time": "start_time",
                "end_time": "end_time", "End Time": "end_time",
                "consultation_fee": "consultation_fee", "Consultation Fee": "consultation_fee",
                "status": "status", "Status": "status",
                "qualification": "qualification", "Qualification": "qualification",
                "registration_no": "registration_no", "Registration No": "registration_no",
                "phone": "phone", "Phone": "phone",
                "email": "email", "Email": "email",
                "photo": "photo", "Photo": "photo",
                "signature": "signature", "Signature": "signature",
                "bio": "bio", "Bio": "bio",
            }
            for k, v in updates.items():
                attr = key_map.get(k)
                if attr and hasattr(doc, attr):
                    setattr(doc, attr, str(v).strip())

            session.commit()
            return self._to_dict(doc)

    def set_doctor_status(self, doctor_id: str, status: str) -> bool:
        """Activate or deactivate doctor."""
        res = self.update_doctor(doctor_id, {"Status": status})
        return res is not None

    def _to_dict(self, d: Doctor) -> Dict[str, str]:
        return {
            "Doctor ID": d.doctor_id,
            "Doctor Name": d.name,
            "Specialization": d.specialization,
            "Available Days": d.available_days or "Monday - Friday",
            "Start Time": d.start_time or "10:00 AM",
            "End Time": d.end_time or "01:00 PM",
            "Consultation Fee": str(d.consultation_fee or "500"),
            "Status": d.status or "Active",
            "Qualification": d.qualification or "",
            "Registration No": d.registration_no or "",
            "Phone": d.phone or "",
            "Email": d.email or "",
            "Photo": d.photo or "",
            "Signature": d.signature or "",
            "Bio": d.bio or "",
            "bio": d.bio or "",
        }


# ---------------------------------------------------------------------------
# 3. PostgreSQL Slot Repository
# ---------------------------------------------------------------------------

class PostgresSlotRepository:
    """PostgreSQL-backed slot repository with row-level locking for concurrency."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self._booking_lock = RLock()

    def invalidate_cache(self) -> None:
        pass

    def list_all_slots(self) -> List[Dict[str, str]]:
        """Return all appointment slots for the active tenant."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            stmt = (
                select(AppointmentSlot, Doctor)
                .join(Doctor, AppointmentSlot.doctor_id == Doctor.id)
                .where(AppointmentSlot.tenant_id == tenant_id)
                .order_by(AppointmentSlot.date, AppointmentSlot.start_time)
            )
            rows = session.execute(stmt).all()
            return [self._to_dict(slot, doc) for slot, doc in rows]

    def get_available_slots(self, doctor: str, date: str) -> List[Dict[str, str]]:
        """Return available slots for a given doctor and date."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            stmt = (
                select(AppointmentSlot, Doctor)
                .join(Doctor, AppointmentSlot.doctor_id == Doctor.id)
                .where(
                    AppointmentSlot.tenant_id == tenant_id,
                    AppointmentSlot.date == date.strip(),
                    AppointmentSlot.status.ilike("available"),
                    or_(
                        Doctor.name.ilike(f"%{doctor.strip()}%"),
                        Doctor.doctor_id == doctor.strip(),
                    ),
                )
                .order_by(AppointmentSlot.start_time)
            )
            rows = session.execute(stmt).all()
            return [self._to_dict(slot, doc) for slot, doc in rows]

    def get_upcoming_available_slots(
        self,
        doctor_name: str = "",
        doctor_id: str = "",
        from_date: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Return upcoming available slots."""
        tenant_id = _resolve_tenant_id()
        today = from_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.session_factory() as session:
            stmt = (
                select(AppointmentSlot, Doctor)
                .join(Doctor, AppointmentSlot.doctor_id == Doctor.id)
                .where(
                    AppointmentSlot.tenant_id == tenant_id,
                    AppointmentSlot.date >= today,
                    AppointmentSlot.status.ilike("available"),
                )
            )
            if doctor_id:
                stmt = stmt.where(Doctor.doctor_id == doctor_id.strip())
            elif doctor_name:
                stmt = stmt.where(Doctor.name.ilike(f"%{doctor_name.strip()}%"))

            stmt = stmt.order_by(AppointmentSlot.date, AppointmentSlot.start_time)
            rows = session.execute(stmt).all()
            return [self._to_dict(slot, doc) for slot, doc in rows]

    def get_slot_by_id(self, slot_id: str, force_refresh: bool = False) -> Optional[Dict[str, str]]:
        """Fetch slot by slot_id."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            stmt = (
                select(AppointmentSlot, Doctor)
                .join(Doctor, AppointmentSlot.doctor_id == Doctor.id)
                .where(
                    AppointmentSlot.tenant_id == tenant_id,
                    or_(AppointmentSlot.slot_id == slot_id.strip(), AppointmentSlot.id == slot_id.strip()),
                )
            )
            row = session.execute(stmt).first()
            return self._to_dict(row[0], row[1]) if row else None

    def get_slot(self, slot_id: str) -> Dict[str, Any]:
        """Facade method returning dict format."""
        slot = self.get_slot_by_id(slot_id)
        return {"success": bool(slot), "slot": slot, "error_code": None if slot else "SLOT_NOT_FOUND"}

    def get_booked_slots(self, doctor: str, date: str) -> List[Dict[str, str]]:
        """Fetch booked slots for a doctor and date."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            stmt = (
                select(AppointmentSlot, Doctor)
                .join(Doctor, AppointmentSlot.doctor_id == Doctor.id)
                .where(
                    AppointmentSlot.tenant_id == tenant_id,
                    AppointmentSlot.date == date.strip(),
                    AppointmentSlot.status.ilike("booked"),
                    or_(Doctor.name.ilike(doctor.strip()), Doctor.doctor_id == doctor.strip()),
                )
            )
            rows = session.execute(stmt).all()
            return [self._to_dict(slot, doc) for slot, doc in rows]

    def book_slot(self, slot_id: str, patient_id: str, token_no: str) -> bool:
        """Atomically lock and book slot using PostgreSQL FOR UPDATE."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            try:
                slot = session.execute(
                    select(AppointmentSlot).where(
                        AppointmentSlot.tenant_id == tenant_id,
                        or_(AppointmentSlot.slot_id == slot_id.strip(), AppointmentSlot.id == slot_id.strip()),
                    ).with_for_update()
                ).scalar_one_or_none()

                if not slot or slot.status.casefold() != "available":
                    return False

                slot.status = "booked"
                slot.booked_patient_id = patient_id.strip()
                slot.booked_token_no = token_no.strip()
                session.commit()
                return True
            except Exception:
                session.rollback()
                return False

    def release_slot_if_needed(self, slot_id: str, patient_id: Optional[str] = None) -> bool:
        """Release a booked slot back to available."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            try:
                slot = session.execute(
                    select(AppointmentSlot).where(
                        AppointmentSlot.tenant_id == tenant_id,
                        or_(AppointmentSlot.slot_id == slot_id.strip(), AppointmentSlot.id == slot_id.strip()),
                    ).with_for_update()
                ).scalar_one_or_none()

                if not slot:
                    return False
                if patient_id and slot.booked_patient_id and slot.booked_patient_id != patient_id:
                    return False

                slot.status = "available"
                slot.booked_patient_id = None
                slot.booked_token_no = None
                session.commit()
                return True
            except Exception:
                session.rollback()
                return False

    def release_slot(self, slot_id: str, patient_id: Optional[str] = None) -> Dict[str, Any]:
        """Facade method for releasing slot."""
        success = self.release_slot_if_needed(slot_id, patient_id)
        return {"success": success, "slot_id": slot_id, "status": "available" if success else "unchanged"}

    def find_slot_by_booking(
        self,
        token_no: Optional[str] = None,
        patient_id: Optional[str] = None,
        doctor_name: Optional[str] = None,
        date: Optional[str] = None,
        start_time: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """Find slot by token, patient, or schedule coordinates."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            stmt = (
                select(AppointmentSlot, Doctor)
                .join(Doctor, AppointmentSlot.doctor_id == Doctor.id)
                .where(AppointmentSlot.tenant_id == tenant_id)
            )
            if token_no:
                stmt = stmt.where(AppointmentSlot.booked_token_no == token_no.strip())
            elif patient_id:
                stmt = stmt.where(AppointmentSlot.booked_patient_id == patient_id.strip())
            elif doctor_name and date and start_time:
                stmt = stmt.where(
                    Doctor.name.ilike(doctor_name.strip()),
                    AppointmentSlot.date == date.strip(),
                    AppointmentSlot.start_time == start_time.strip(),
                )

            row = session.execute(stmt).first()
            return self._to_dict(row[0], row[1]) if row else None

    def create_slot(self, data: Dict[str, str]) -> Dict[str, str]:
        """Create new appointment slot in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            doc_id = str(data.get("Doctor ID") or data.get("doctor_id") or "").strip()
            doc_name = str(data.get("Doctor Name") or data.get("doctor_name") or "").strip()
            conds = []
            if doc_id:
                conds.extend([Doctor.doctor_id == doc_id, Doctor.id == doc_id])
            if doc_name:
                conds.append(Doctor.name.ilike(doc_name))
            if not conds:
                conds.append(Doctor.doctor_id != "")

            doc = session.execute(
                select(Doctor).where(
                    Doctor.tenant_id == tenant_id,
                    or_(*conds),
                )
            ).scalars().first()
            if not doc:
                raise ValueError(f"Doctor '{doc_id or doc_name}' not found")

            sid = data.get("Slot ID") or data.get("slot_id") or f"SLOT{uuid4().hex[:6].upper()}"
            slot = AppointmentSlot(
                tenant_id=tenant_id,
                slot_id=sid,
                doctor_id=doc.id,
                date=data.get("Date") or data.get("date", ""),
                start_time=data.get("Start Time") or data.get("start_time", ""),
                end_time=data.get("End Time") or data.get("end_time", ""),
                status=(data.get("Status") or data.get("status", "available")).casefold(),
            )
            session.add(slot)
            session.commit()
            return self._to_dict(slot, doc)

    def update_slot(self, slot_id: str, updates: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Update slot fields in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            slot = session.execute(
                select(AppointmentSlot).where(
                    AppointmentSlot.tenant_id == tenant_id,
                    or_(AppointmentSlot.slot_id == slot_id.strip(), AppointmentSlot.id == slot_id.strip()),
                )
            ).scalar_one_or_none()
            if not slot:
                return None

            new_status = updates.get("Status") or updates.get("status")
            if slot.status.casefold() == "booked" and new_status and new_status.casefold() == "available":
                if slot.booked_patient_id and "force" not in updates:
                    raise ValueError("Cannot mark an actively booked slot as available without releasing the appointment")

            if new_status: slot.status = new_status.casefold()
            if "date" in updates or "Date" in updates:
                slot.date = (updates.get("Date") or updates.get("date", "")).strip()
            if "start_time" in updates or "Start Time" in updates:
                slot.start_time = (updates.get("Start Time") or updates.get("start_time", "")).strip()
            if "end_time" in updates or "End Time" in updates:
                slot.end_time = (updates.get("End Time") or updates.get("end_time", "")).strip()

            session.commit()
            doc = session.execute(select(Doctor).where(Doctor.id == slot.doctor_id)).scalar_one_or_none()
            return self._to_dict(slot, doc)

    def set_slot_status(self, slot_id: str, status: str) -> bool:
        """Update slot status."""
        res = self.update_slot(slot_id, {"Status": status})
        return res is not None

    def _to_dict(self, slot: AppointmentSlot, doc: Optional[Doctor]) -> Dict[str, str]:
        return {
            "Slot ID": slot.slot_id,
            "Doctor ID": doc.doctor_id if doc else "",
            "Doctor Name": doc.name if doc else "",
            "Date": slot.date,
            "Start Time": slot.start_time,
            "End Time": slot.end_time,
            "Status": slot.status.capitalize(),
            "Patient ID": slot.booked_patient_id or "",
            "Token No": slot.booked_token_no or "",
            "Booked At": slot.updated_at.isoformat() if slot.status.casefold() == "booked" and slot.updated_at else "",
        }


# ---------------------------------------------------------------------------
# 4. PostgreSQL Prescription Service
# ---------------------------------------------------------------------------

class PostgresPrescriptionService:
    """PostgreSQL-backed prescription service storing drafts, versions, and items directly in PostgreSQL."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        pdf_dir: Optional[Path] = None,
        audit_service=None,
    ) -> None:
        self.session_factory = session_factory
        root_dir = Path(__file__).resolve().parents[2]
        self.pdf_dir = pdf_dir or (root_dir / "data" / "prescriptions")
        self.audit = audit_service or PostgresAuditService(session_factory)
        self._lock = RLock()

    def validate_medicines(self, medicines: list[dict], allow_empty: bool = True) -> list[dict]:
        """Sanitize and validate medicine items."""
        if not medicines and not allow_empty:
            raise ValueError("Prescription must include at least one medication.")

        cleaned = []
        for idx, med in enumerate(medicines, start=1):
            name = str(med.get("name", "")).strip()
            strength = str(med.get("strength", "")).strip()
            dosage = str(med.get("dosage", "")).strip()
            frequency = str(med.get("frequency", "")).strip()
            duration = str(med.get("duration", "")).strip()
            instructions = str(med.get("instructions", "")).strip()

            if not allow_empty:
                if not name:
                    raise ValueError(f"Medicine row {idx} is missing a medicine name.")
                if not dosage:
                    raise ValueError(f"Medicine row {idx} ('{name}') is missing dosage information.")
                if not frequency:
                    raise ValueError(f"Medicine row {idx} ('{name}') is missing frequency instructions.")
                if not duration:
                    raise ValueError(f"Medicine row {idx} ('{name}') is missing duration.")

            if name:
                cleaned.append({
                    "name": name,
                    "strength": strength,
                    "dosage": dosage,
                    "frequency": frequency,
                    "duration": duration,
                    "instructions": instructions,
                })

        if not allow_empty and not cleaned:
            raise ValueError("Prescription must contain at least one valid medication.")
        return cleaned

    def create_or_update_draft(
        self,
        data: dict,
        doctor_id: str,
        doctor_name: str,
        doctor_specialization: str = "",
        doctor_qualification: str = "",
        doctor_reg_no: str = "",
        user: str = "doctor",
    ) -> dict:
        """Save prescription as draft in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self._lock, self.session_factory() as session:
            try:
                rx_id = str(data.get("prescription_id", "")).strip()
                now = datetime.now(timezone.utc)

                # 1. Resolve Doctor
                doc = session.execute(
                    select(Doctor).where(
                        Doctor.tenant_id == tenant_id,
                        or_(
                            Doctor.doctor_id == doctor_id.strip(),
                            Doctor.id == doctor_id.strip(),
                            Doctor.name.ilike(doctor_name.strip()),
                        ),
                    )
                ).scalars().first()

                if not doc:
                    # Create doctor if not yet in table
                    doc = Doctor(
                        tenant_id=tenant_id,
                        doctor_id=doctor_id.strip(),
                        name=doctor_name.strip(),
                        specialization=doctor_specialization.strip() or "General Physician",
                        qualification=doctor_qualification.strip(),
                        registration_no=doctor_reg_no.strip(),
                        status="Active",
                    )
                    session.add(doc)
                    session.flush()

                # 2. Resolve Patient
                pat_id_str = str(data.get("patient_id", "")).strip()
                pat = None
                if pat_id_str:
                    pat = session.execute(
                        select(Patient).where(
                            Patient.tenant_id == tenant_id,
                            or_(Patient.patient_id == pat_id_str, Patient.id == pat_id_str),
                        )
                    ).scalars().first()
                if not pat:
                    pname = str(data.get("patient_name", "")).strip() or "Patient"
                    pphone = str(data.get("patient_phone", "")).strip()
                    pid = pat_id_str or f"PAT-{uuid4().hex[:12].upper()}"
                    pat = Patient(
                        tenant_id=tenant_id,
                        patient_id=pid,
                        name=pname,
                        phone=pphone,
                        email=str(data.get("patient_email", "")).strip() or None,
                        age=str(data.get("patient_age", "")).strip() or None,
                        gender=str(data.get("patient_gender", "")).strip() or None,
                        status="Active",
                    )
                    session.add(pat)
                    session.flush()

                # 3. Resolve Appointment
                appt_id_str = str(data.get("appointment_id", "")).strip()
                appt = None
                if appt_id_str:
                    appt = session.execute(
                        select(Appointment).where(
                            Appointment.tenant_id == tenant_id,
                            or_(Appointment.token_no == appt_id_str, Appointment.id == appt_id_str),
                        )
                    ).scalars().first()
                    if not appt:
                        appt = Appointment(
                            tenant_id=tenant_id,
                            token_no=appt_id_str,
                            patient_id=pat.id,
                            doctor_id=doc.id,
                            appointment_date=str(data.get("date", now.strftime("%Y-%m-%d"))).strip(),
                            appointment_time="10:00 AM",
                            amount="500",
                            payment_method="Offline",
                            payment_status="Pending",
                            booking_status="Confirmed",
                        )
                        session.add(appt)
                        session.flush()

                # 4. Check existing prescription
                rx_row = None
                if rx_id:
                    rx_row = session.execute(
                        select(Prescription).where(
                            Prescription.tenant_id == tenant_id,
                            or_(Prescription.prescription_id == rx_id, Prescription.id == rx_id),
                        )
                    ).scalars().first()

                if rx_row:
                    # Enforce isolation: only owner can edit
                    is_owner = False
                    if doc and rx_row.doctor_id == doc.id:
                        is_owner = True
                    elif rx_row.doctor and (rx_row.doctor.doctor_id.casefold() == doctor_id.strip().casefold() or rx_row.doctor.id == doctor_id.strip()):
                        is_owner = True
                    elif rx_row.created_by and user and rx_row.created_by.casefold() == user.strip().casefold():
                        is_owner = True
                    if not is_owner:
                        raise PermissionError("Access forbidden: You cannot modify another physician's prescription.")
                    if rx_row.status in ("finalized", "amended"):
                        raise ValueError("Cannot edit a finalized prescription as a draft. Please create an amendment.")
                else:
                    rx_id = rx_id or f"RX-{uuid4().hex[:10].upper()}"
                    rx_row = Prescription(
                        tenant_id=tenant_id,
                        prescription_id=rx_id,
                        patient_id=pat.id,
                        doctor_id=doc.id,
                        appointment_id=appt.id if appt else None,
                        date=str(data.get("date", now.strftime("%Y-%m-%d"))).strip(),
                        version=1,
                        status="draft",
                        created_by=user,
                        version_history=[],
                        email_delivery=None,
                    )
                    session.add(rx_row)
                    session.flush()

                # Update prescription fields
                rx_row.patient_id = pat.id
                rx_row.doctor_id = doc.id
                if appt: rx_row.appointment_id = appt.id
                rx_row.date = str(data.get("date", rx_row.date)).strip()
                rx_row.chief_complaints = str(data.get("chief_complaints", "")).strip()
                rx_row.diagnosis = str(data.get("diagnosis", "")).strip()
                rx_row.symptoms = str(data.get("symptoms", "")).strip()
                rx_row.vitals = data.get("vitals") if isinstance(data.get("vitals"), dict) else {}
                rx_row.clinical_notes = str(data.get("clinical_notes", "")).strip()
                rx_row.tests_advised = str(data.get("tests_advised", "")).strip()
                rx_row.advice = str(data.get("advice", "")).strip()
                rx_row.follow_up_date = str(data.get("follow_up_date", "")).strip()
                rx_row.updated_by = user
                rx_row.status = "draft"

                # Overwrite medicines
                cleaned_meds = self.validate_medicines(data.get("medicines", []), allow_empty=True)
                session.execute(delete(PrescriptionItem).where(PrescriptionItem.prescription_id == rx_row.id))
                for idx, med in enumerate(cleaned_meds, start=1):
                    item = PrescriptionItem(
                        prescription_id=rx_row.id,
                        order_index=idx,
                        name=med["name"],
                        strength=med.get("strength"),
                        dosage=med.get("dosage"),
                        frequency=med.get("frequency"),
                        duration=med.get("duration"),
                        instructions=med.get("instructions"),
                    )
                    session.add(item)

                session.commit()

                self.audit.record(
                    user=user,
                    action="PRESCRIPTION_DRAFT_SAVE",
                    entity_type="prescription",
                    entity_id=rx_row.prescription_id,
                    details={
                        "patient_id": pat.patient_id,
                        "appointment_id": appt.token_no if appt else appt_id_str,
                        "status": "draft",
                    },
                )
                return self._to_dict(rx_row, pat, doc, appt, cleaned_meds)
            except Exception as e:
                session.rollback()
                raise e

    def finalize_prescription(
        self,
        prescription_id: str,
        doctor_id: str,
        user: str = "doctor",
    ) -> dict:
        """Review and finalize a prescription with clinical validation."""
        tenant_id = _resolve_tenant_id()
        with self._lock, self.session_factory() as session:
            rx = session.execute(
                select(Prescription).where(
                    Prescription.tenant_id == tenant_id,
                    or_(Prescription.prescription_id == prescription_id.strip(), Prescription.id == prescription_id.strip()),
                )
            ).scalars().first()

            if not rx:
                raise ValueError(f"Prescription '{prescription_id}' not found.")

            doc = session.execute(select(Doctor).where(Doctor.id == rx.doctor_id)).scalar_one_or_none()
            is_owner = False
            if doc and (doc.doctor_id.casefold() == doctor_id.strip().casefold() or doc.id == doctor_id.strip()):
                is_owner = True
            elif rx.created_by and user and rx.created_by.casefold() == user.strip().casefold():
                is_owner = True

            if not is_owner:
                raise PermissionError("Access forbidden: You cannot finalize another physician's prescription.")

            if rx.status in ("finalized", "amended"):
                pat = session.execute(select(Patient).where(Patient.id == rx.patient_id)).scalar_one_or_none()
                appt = session.execute(select(Appointment).where(Appointment.id == rx.appointment_id)).scalar_one_or_none() if rx.appointment_id else None
                meds = [self._med_to_dict(it) for it in rx.items]
                return self._to_dict(rx, pat, doc, appt, meds)

            pat = session.execute(select(Patient).where(Patient.id == rx.patient_id)).scalar_one_or_none()
            appt = session.execute(select(Appointment).where(Appointment.id == rx.appointment_id)).scalar_one_or_none() if rx.appointment_id else None

            # Strict clinical validation prior to finalization
            if not pat or not pat.patient_id:
                raise ValueError("Patient ID is required before finalizing prescription.")
            if not pat or not pat.name:
                raise ValueError("Patient Name is required before finalizing prescription.")
            if not appt or not appt.token_no:
                raise ValueError("Appointment Token/ID is required before finalizing prescription.")
            if not rx.diagnosis or not rx.diagnosis.strip():
                raise ValueError("Clinical Diagnosis is required before finalizing prescription.")

            # Must have at least 1 complete medicine
            current_meds = [self._med_to_dict(it) for it in rx.items]
            validated_meds = self.validate_medicines(current_meds, allow_empty=False)

            now = datetime.now(timezone.utc)
            rx.status = "finalized"
            rx.finalized_at = now
            rx.updated_by = user
            session.commit()

            self.audit.record(
                user=user,
                action="PRESCRIPTION_FINALIZE",
                entity_type="prescription",
                entity_id=rx.prescription_id,
                details={
                    "patient_id": pat.patient_id,
                    "appointment_id": appt.token_no if appt else "",
                    "version": rx.version,
                },
            )
            return self._to_dict(rx, pat, doc, appt, validated_meds)

    def amend_prescription(
        self,
        prescription_id: str,
        updates: dict,
        doctor_id: str,
        user: str = "doctor",
        amendment_reason: str = "Clinical dosage correction",
    ) -> dict:
        """Amend an already finalized prescription with version history."""
        tenant_id = _resolve_tenant_id()
        with self._lock, self.session_factory() as session:
            rx = session.execute(
                select(Prescription).where(
                    Prescription.tenant_id == tenant_id,
                    or_(Prescription.prescription_id == prescription_id.strip(), Prescription.id == prescription_id.strip()),
                )
            ).scalars().first()

            if not rx:
                raise ValueError(f"Prescription '{prescription_id}' not found.")

            doc = session.execute(select(Doctor).where(Doctor.id == rx.doctor_id)).scalar_one_or_none()
            is_owner = False
            if doc and (doc.doctor_id.casefold() == doctor_id.strip().casefold() or doc.id == doctor_id.strip()):
                is_owner = True
            elif rx.created_by and user and rx.created_by.casefold() == user.strip().casefold():
                is_owner = True

            if not is_owner:
                raise PermissionError("Access forbidden: You cannot amend another physician's prescription.")

            if rx.status not in ("finalized", "amended"):
                raise ValueError("Only finalized prescriptions can be amended. Edit the draft instead.")

            if not amendment_reason or not amendment_reason.strip():
                raise ValueError("A clear reason for the clinical amendment must be provided.")

            now = datetime.now(timezone.utc)
            current_meds = [self._med_to_dict(it) for it in rx.items]

            # Snapshot previous finalized version
            snapshot = {
                "version": rx.version,
                "chief_complaints": rx.chief_complaints or "",
                "diagnosis": rx.diagnosis or "",
                "symptoms": rx.symptoms or "",
                "vitals": dict(rx.vitals or {}),
                "clinical_notes": rx.clinical_notes or "",
                "medicines": list(current_meds),
                "tests_advised": rx.tests_advised or "",
                "advice": rx.advice or "",
                "follow_up_date": rx.follow_up_date or "",
                "finalized_at": rx.finalized_at.isoformat() if rx.finalized_at else now.isoformat(),
                "amended_at": now.isoformat(),
                "amended_by": user,
                "amendment_reason": amendment_reason.strip(),
            }
            v_hist = list(rx.version_history or [])
            v_hist.append(snapshot)
            rx.version_history = v_hist

            # Apply updates
            rx.version += 1
            rx.status = "amended"
            rx.updated_by = user
            rx.finalized_at = now

            if "chief_complaints" in updates: rx.chief_complaints = str(updates["chief_complaints"]).strip()
            if "diagnosis" in updates and str(updates["diagnosis"]).strip(): rx.diagnosis = str(updates["diagnosis"]).strip()
            if "symptoms" in updates: rx.symptoms = str(updates["symptoms"]).strip()
            if "vitals" in updates and isinstance(updates["vitals"], dict): rx.vitals = updates["vitals"]
            if "clinical_notes" in updates: rx.clinical_notes = str(updates["clinical_notes"]).strip()
            if "tests_advised" in updates: rx.tests_advised = str(updates["tests_advised"]).strip()
            if "advice" in updates: rx.advice = str(updates["advice"]).strip()
            if "follow_up_date" in updates: rx.follow_up_date = str(updates["follow_up_date"]).strip()

            if "medicines" in updates:
                new_meds = self.validate_medicines(updates["medicines"], allow_empty=False)
                session.execute(delete(PrescriptionItem).where(PrescriptionItem.prescription_id == rx.id))
                for idx, med in enumerate(new_meds, start=1):
                    item = PrescriptionItem(
                        prescription_id=rx.id,
                        order_index=idx,
                        name=med["name"],
                        strength=med.get("strength"),
                        dosage=med.get("dosage"),
                        frequency=med.get("frequency"),
                        duration=med.get("duration"),
                        instructions=med.get("instructions"),
                    )
                    session.add(item)
                current_meds = new_meds

            session.commit()

            self.audit.record(
                user=user,
                action="PRESCRIPTION_AMENDMENT",
                entity_type="prescription",
                entity_id=rx.prescription_id,
                details={
                    "new_version": rx.version,
                    "reason": amendment_reason.strip(),
                },
            )
            pat = session.execute(select(Patient).where(Patient.id == rx.patient_id)).scalar_one_or_none()
            appt = session.execute(select(Appointment).where(Appointment.id == rx.appointment_id)).scalar_one_or_none() if rx.appointment_id else None
            return self._to_dict(rx, pat, doc, appt, current_meds)

    def get_prescription(self, prescription_id: str) -> Optional[dict]:
        """Fetch prescription by ID from PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            rx = session.execute(
                select(Prescription).where(
                    Prescription.tenant_id == tenant_id,
                    or_(Prescription.prescription_id == prescription_id.strip(), Prescription.id == prescription_id.strip()),
                )
            ).scalars().first()
            if not rx:
                return None
            pat = session.execute(select(Patient).where(Patient.id == rx.patient_id)).scalar_one_or_none()
            doc = session.execute(select(Doctor).where(Doctor.id == rx.doctor_id)).scalar_one_or_none()
            appt = session.execute(select(Appointment).where(Appointment.id == rx.appointment_id)).scalar_one_or_none() if rx.appointment_id else None
            meds = [self._med_to_dict(it) for it in rx.items]
            return self._to_dict(rx, pat, doc, appt, meds)

    def get_prescription_by_appointment(self, appointment_id: str) -> Optional[dict]:
        """Find prescription associated with a specific appointment token or ID."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            stmt = (
                select(Prescription)
                .outerjoin(Appointment, Prescription.appointment_id == Appointment.id)
                .where(
                    Prescription.tenant_id == tenant_id,
                    or_(
                        Appointment.token_no == appointment_id.strip(),
                        Appointment.id == appointment_id.strip(),
                        Prescription.appointment_id == appointment_id.strip(),
                    ),
                )
            )
            rx = session.execute(stmt).scalars().first()
            if not rx:
                return None
            pat = session.execute(select(Patient).where(Patient.id == rx.patient_id)).scalar_one_or_none()
            doc = session.execute(select(Doctor).where(Doctor.id == rx.doctor_id)).scalar_one_or_none()
            appt = session.execute(select(Appointment).where(Appointment.id == rx.appointment_id)).scalar_one_or_none() if rx.appointment_id else None
            meds = [self._med_to_dict(it) for it in rx.items]
            return self._to_dict(rx, pat, doc, appt, meds)

    def list_prescriptions(
        self,
        doctor_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
        status: Optional[str] = None,
        date_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = 20,
    ) -> Union[list[dict], dict]:
        """List prescriptions with filtering and optional pagination from PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            stmt = (
                select(Prescription, Patient, Doctor, Appointment)
                .join(Patient, Prescription.patient_id == Patient.id)
                .join(Doctor, Prescription.doctor_id == Doctor.id)
                .outerjoin(Appointment, Prescription.appointment_id == Appointment.id)
                .where(Prescription.tenant_id == tenant_id)
            )
            if doctor_id:
                stmt = stmt.where(or_(Doctor.doctor_id == doctor_id.strip(), Doctor.id == doctor_id.strip()))
            if patient_id:
                stmt = stmt.where(or_(Patient.patient_id == patient_id.strip(), Patient.id == patient_id.strip()))
            if appointment_id:
                stmt = stmt.where(or_(Appointment.token_no == appointment_id.strip(), Appointment.id == appointment_id.strip()))
            if status:
                stmt = stmt.where(Prescription.status == status.strip().lower())
            if date_filter:
                stmt = stmt.where(Prescription.date == date_filter.strip())
            if search and search.strip():
                q = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        Patient.name.ilike(q),
                        Patient.patient_id.ilike(q),
                        Doctor.name.ilike(q),
                        Doctor.doctor_id.ilike(q),
                        Prescription.prescription_id.ilike(q),
                        Prescription.diagnosis.ilike(q),
                    )
                )

            stmt = stmt.order_by(Prescription.date.desc(), Prescription.created_at.desc())

            if page is not None and page >= 1:
                p_size = max(1, min(page_size or 20, 100))
                count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
                total = session.execute(count_stmt).scalar_one()

                paged_stmt = stmt.offset((page - 1) * p_size).limit(p_size)
                rows = session.execute(paged_stmt).all()
                results = []
                for rx, pat, doc, appt in rows:
                    meds = [self._med_to_dict(it) for it in rx.items]
                    results.append(self._to_dict(rx, pat, doc, appt, meds))

                return {
                    "prescriptions": results,
                    "total": total,
                    "page": page,
                    "page_size": p_size,
                    "total_pages": max(1, math.ceil(total / p_size)) if total > 0 else 1,
                }

            rows = session.execute(stmt).all()
            results = []
            for rx, pat, doc, appt in rows:
                meds = [self._med_to_dict(it) for it in rx.items]
                results.append(self._to_dict(rx, pat, doc, appt, meds))
            return results

    def record_email_delivery(
        self,
        prescription_id: str,
        success: bool,
        recipient: str,
        error: Optional[str] = None,
    ) -> None:
        """Track prescription email delivery state in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self._lock, self.session_factory() as session:
            rx = session.execute(
                select(Prescription).where(
                    Prescription.tenant_id == tenant_id,
                    or_(Prescription.prescription_id == prescription_id.strip(), Prescription.id == prescription_id.strip()),
                )
            ).scalars().first()
            if not rx:
                return
            now = datetime.now(timezone.utc)
            rx.email_delivery = {
                "sent": success,
                "sent_at": now.isoformat() if success else None,
                "recipient": recipient,
                "error": error,
            }
            session.commit()

    def generate_pdf_for_prescription(
        self,
        prescription_id: str,
        clinic_name: str = "Clinic",
        clinic_phone: str = "",
        clinic_email: str = "",
        clinic_address: str = "",
        clinic_logo: str = "",
        doctor_signature: str = "",
    ) -> tuple[str, Path]:
        """Generate a ReportLab PDF document for a prescription, caching generated PDFs."""
        rx = self.get_prescription(prescription_id)
        if not rx:
            raise ValueError(f"Prescription '{prescription_id}' not found.")

        clean_id = prescription_id.replace("/", "_").replace("\\", "_")
        version = rx.get("version", 1)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        cached_pdf_path = self.pdf_dir / f"{clean_id}_v{version}.pdf"

        if rx.get("status") in ("finalized", "amended") and cached_pdf_path.exists() and cached_pdf_path.stat().st_size > 0:
            return clean_id, cached_pdf_path

        # Lookup doctor signature, photo and clinic logo from database
        tenant_id = _resolve_tenant_id()
        effective_logo = clinic_logo
        effective_sig = doctor_signature
        effective_photo = ""

        doc_qual = rx.get("doctor_qualification") or ""
        doc_reg = rx.get("doctor_reg_no") or ""

        with self.session_factory() as session:
            doc_row = session.execute(
                select(Doctor).where(
                    Doctor.tenant_id == tenant_id,
                    or_(Doctor.doctor_id == rx.get("doctor_id", ""), Doctor.id == rx.get("doctor_id", "")),
                )
            ).scalars().first()
            if doc_row:
                if not effective_sig:
                    effective_sig = doc_row.signature or ""
                effective_photo = doc_row.photo or ""
                if not doc_qual:
                    doc_qual = doc_row.qualification or ""
                if not doc_reg:
                    doc_reg = doc_row.registration_no or ""

            if not effective_logo:
                clinic_row = session.execute(
                    select(Clinic).where(Clinic.id == tenant_id)
                ).scalars().first()
                if clinic_row:
                    effective_logo = clinic_row.logo or ""
                    if not clinic_name or clinic_name == "Clinic":
                        clinic_name = clinic_row.name

        pdf_data = PrescriptionPDFData(
            clinic_name=clinic_name,
            clinic_phone=clinic_phone,
            clinic_email=clinic_email,
            clinic_address=clinic_address,
            doctor_name=rx.get("doctor_name", "Doctor"),
            doctor_specialization=rx.get("doctor_specialization", "Physician"),
            doctor_qualification=doc_qual,
            doctor_reg_no=doc_reg,
            patient_id=rx.get("patient_id", ""),
            patient_name=rx.get("patient_name", ""),
            patient_phone=rx.get("patient_phone", ""),
            patient_age=rx.get("patient_age", ""),
            patient_gender=rx.get("patient_gender", ""),
            appointment_id=rx.get("appointment_id", ""),
            prescription_id=rx.get("prescription_id", ""),
            date=rx.get("date", ""),
            chief_complaints=rx.get("chief_complaints", ""),
            diagnosis=rx.get("diagnosis", ""),
            symptoms=rx.get("symptoms", ""),
            vitals=rx.get("vitals", {}),
            clinical_notes=rx.get("clinical_notes", ""),
            medicines=rx.get("medicines", []),
            tests_advised=rx.get("tests_advised", ""),
            advice=rx.get("advice", ""),
            follow_up_date=rx.get("follow_up_date", ""),
            version=rx.get("version", 1),
            clinic_logo=effective_logo or rx.get("clinic_logo", ""),
            doctor_signature=effective_sig or rx.get("doctor_signature", "") or rx.get("Signature", ""),
            doctor_photo=effective_photo or rx.get("doctor_photo", "") or rx.get("Photo", ""),
        )

        rx_num, pdf_file = generate_prescription_pdf(pdf_data, self.pdf_dir)

        # Update pdf_path in database
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            rx_record = session.execute(
                select(Prescription).where(
                    Prescription.tenant_id == tenant_id,
                    or_(Prescription.prescription_id == prescription_id.strip(), Prescription.id == prescription_id.strip()),
                )
            ).scalars().first()
            if rx_record:
                rx_record.pdf_path = str(pdf_file)
                session.commit()

        return rx_num, pdf_file

    def _med_to_dict(self, it: PrescriptionItem) -> dict:
        return {
            "name": it.name,
            "strength": it.strength or "",
            "dosage": it.dosage or "",
            "frequency": it.frequency or "",
            "duration": it.duration or "",
            "instructions": it.instructions or "",
        }

    def _to_dict(
        self,
        rx: Prescription,
        pat: Optional[Patient],
        doc: Optional[Doctor],
        appt: Optional[Appointment],
        meds: list[dict],
    ) -> dict:
        return {
            "prescription_id": rx.prescription_id,
            "created_at": rx.created_at.isoformat() if rx.created_at else "",
            "created_by": rx.created_by or "doctor",
            "version": rx.version,
            "version_history": rx.version_history or [],
            "email_delivery": rx.email_delivery,
            "patient_id": pat.patient_id if pat else "",
            "patient_name": pat.name if pat else "",
            "patient_phone": pat.phone if pat else "",
            "patient_email": pat.email or "" if pat else "",
            "patient_age": str(pat.age or "") if pat else "",
            "patient_gender": pat.gender or "" if pat else "",
            "doctor_id": doc.doctor_id if doc else "",
            "doctor_name": doc.name if doc else "",
            "doctor_specialization": doc.specialization if doc else "",
            "doctor_qualification": doc.qualification or "" if doc else "",
            "doctor_reg_no": doc.registration_no or "" if doc else "",
            "appointment_id": appt.token_no if appt else (rx.appointment_id or ""),
            "date": rx.date,
            "chief_complaints": rx.chief_complaints or "",
            "diagnosis": rx.diagnosis or "",
            "symptoms": rx.symptoms or "",
            "vitals": rx.vitals or {},
            "clinical_notes": rx.clinical_notes or "",
            "medicines": meds,
            "tests_advised": rx.tests_advised or "",
            "advice": rx.advice or "",
            "follow_up_date": rx.follow_up_date or "",
            "status": rx.status,
            "updated_at": rx.updated_at.isoformat() if rx.updated_at else "",
            "updated_by": rx.updated_by or "doctor",
            "finalized_at": rx.finalized_at.isoformat() if rx.finalized_at else None,
            "pdf_path": rx.pdf_path,
        }


# ---------------------------------------------------------------------------
# 5. PostgreSQL Doctor Account Service
# ---------------------------------------------------------------------------

class PostgresDoctorAccountService:
    """PostgreSQL-backed doctor account service managing users with role='doctor' in PostgreSQL."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        doctor_directory=None,
        audit_service=None,
        allow_demo_password: bool = False,
    ) -> None:
        self.session_factory = session_factory
        self.doctor_directory = doctor_directory
        self.audit = audit_service or PostgresAuditService(session_factory)
        self.allow_demo_password = allow_demo_password
        self._lock = RLock()

    def validate_password_strength(self, password: str) -> None:
        """Validate password meets security policies unless demo password is explicitly allowed."""
        if self.allow_demo_password and password == "1234":
            return
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[a-zA-Z]", password):
            raise ValueError("Password must contain at least one letter.")

    def create_account(
        self,
        username: str,
        password: str,
        doctor_id: str,
        email: str = "",
        admin_user: str = "admin",
    ) -> dict:
        """Create a new doctor account in PostgreSQL linked to a valid Doctor Directory record."""
        norm_username = username.strip().casefold()
        if not norm_username:
            raise ValueError("Username is required.")
        if not re.match(r"^[a-zA-Z0-9_\-\.]{3,32}$", username.strip()):
            raise ValueError("Username must be 3-32 characters (alphanumeric, dots, dashes, underscores).")

        norm_doctor_id = doctor_id.strip()
        if not norm_doctor_id:
            raise ValueError("Doctor ID is required.")

        tenant_id = _resolve_tenant_id()
        with self._lock, self.session_factory() as session:
            # Check if username exists in tenant
            exists_user = session.execute(
                select(User).where(User.tenant_id == tenant_id, User.username == norm_username)
            ).scalar_one_or_none()
            if exists_user:
                raise ValueError(f"Account with username '{username.strip()}' already exists.")

            # Look up doctor
            doc = session.execute(
                select(Doctor).where(
                    Doctor.tenant_id == tenant_id,
                    or_(Doctor.doctor_id == norm_doctor_id, Doctor.id == norm_doctor_id),
                )
            ).scalars().first()
            if not doc:
                raise ValueError(f"Doctor ID '{norm_doctor_id}' does not exist in the Doctor Directory.")

            # Ensure doctor is not already assigned to another account
            doc_linked = session.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.doctor_id == doc.doctor_id,
                )
            ).scalars().first()
            if doc_linked:
                raise ValueError(f"Doctor ID '{norm_doctor_id}' is already linked to account '{doc_linked.username}'.")

            self.validate_password_strength(password)
            now = datetime.now(timezone.utc)
            hashed = hash_password(password)

            user = User(
                tenant_id=tenant_id,
                username=norm_username,
                password_hash=hashed,
                role="doctor",
                doctor_id=doc.doctor_id,
                full_name=doc.name,
                email=email.strip(),
                status="Active",
                must_change_password=True,
            )
            session.add(user)
            session.commit()

            self.audit.record(
                user=admin_user,
                action="DOCTOR_ACCOUNT_CREATE",
                entity_type="doctor_account",
                entity_id=norm_username,
                details={
                    "doctor_id": doc.doctor_id,
                    "doctor_name": doc.name,
                    "email": email.strip(),
                },
            )
            return self._to_dict(user, doc)

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Verify username & password in PostgreSQL."""
        norm_username = username.strip().casefold()
        tenant_id = _resolve_tenant_id()
        with self._lock, self.session_factory() as session:
            user = session.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.username == norm_username,
                )
            ).scalar_one_or_none()
            if not user or user.status.casefold() != "active":
                return None
            if not verify_password(password, user.password_hash):
                return None

            user.last_login = datetime.now(timezone.utc)
            session.commit()

            doc = session.execute(
                select(Doctor).where(Doctor.tenant_id == tenant_id, Doctor.doctor_id == user.doctor_id)
            ).scalars().first() if user.doctor_id else None
            return self._to_dict(user, doc)

    def change_password(self, username: str, old_password: str, new_password: str) -> dict:
        """Allow doctor to change password in PostgreSQL."""
        norm_username = username.strip().casefold()
        tenant_id = _resolve_tenant_id()
        with self._lock, self.session_factory() as session:
            user = session.execute(
                select(User).where(User.tenant_id == tenant_id, User.username == norm_username)
            ).scalar_one_or_none()
            if not user:
                raise ValueError(f"Account '{username}' not found.")

            if not verify_password(old_password, user.password_hash):
                raise ValueError("Incorrect current password.")

            self.validate_password_strength(new_password)
            user.password_hash = hash_password(new_password)
            user.must_change_password = False
            session.commit()

            self.audit.record(
                user=username,
                action="DOCTOR_PASSWORD_CHANGE",
                entity_type="doctor_account",
                entity_id=norm_username,
                details={"reason": "User initiated password change."},
            )
            doc = session.execute(
                select(Doctor).where(Doctor.tenant_id == tenant_id, Doctor.doctor_id == user.doctor_id)
            ).scalars().first() if user.doctor_id else None
            return self._to_dict(user, doc)

    def reset_password(self, username: str, new_password: str, admin_user: str = "admin") -> dict:
        """Admin resets doctor password in PostgreSQL."""
        norm_username = username.strip().casefold()
        tenant_id = _resolve_tenant_id()
        with self._lock, self.session_factory() as session:
            user = session.execute(
                select(User).where(User.tenant_id == tenant_id, User.username == norm_username)
            ).scalar_one_or_none()
            if not user:
                raise ValueError(f"Account '{username}' not found.")

            self.validate_password_strength(new_password)
            user.password_hash = hash_password(new_password)
            user.must_change_password = True
            session.commit()

            self.audit.record(
                user=admin_user,
                action="DOCTOR_PASSWORD_RESET",
                entity_type="doctor_account",
                entity_id=norm_username,
                details={"reset_by": admin_user},
            )
            doc = session.execute(
                select(Doctor).where(Doctor.tenant_id == tenant_id, Doctor.doctor_id == user.doctor_id)
            ).scalars().first() if user.doctor_id else None
            return self._to_dict(user, doc)

    def update_account(self, username: str, updates: dict, admin_user: str = "admin") -> dict:
        """Update doctor account in PostgreSQL."""
        norm_username = username.strip().casefold()
        tenant_id = _resolve_tenant_id()
        with self._lock, self.session_factory() as session:
            user = session.execute(
                select(User).where(User.tenant_id == tenant_id, User.username == norm_username)
            ).scalar_one_or_none()
            if not user:
                raise ValueError(f"Account '{username}' not found.")

            if "doctor_id" in updates and updates["doctor_id"] != user.doctor_id:
                new_doc_id = updates["doctor_id"].strip()
                doc = session.execute(
                    select(Doctor).where(
                        Doctor.tenant_id == tenant_id,
                        or_(Doctor.doctor_id == new_doc_id, Doctor.id == new_doc_id),
                    )
                ).scalars().first()
                if not doc:
                    raise ValueError(f"Doctor ID '{new_doc_id}' does not exist.")
                user.doctor_id = doc.doctor_id
                user.full_name = doc.name

            if "email" in updates:
                user.email = updates["email"].strip()

            if "status" in updates:
                new_status = updates["status"].strip().title()
                if new_status in ("Active", "Inactive"):
                    user.status = new_status

            session.commit()

            self.audit.record(
                user=admin_user,
                action="DOCTOR_ACCOUNT_UPDATE",
                entity_type="doctor_account",
                entity_id=norm_username,
                details={k: v for k, v in updates.items() if k != "password"},
            )
            doc = session.execute(
                select(Doctor).where(Doctor.tenant_id == tenant_id, Doctor.doctor_id == user.doctor_id)
            ).scalars().first() if user.doctor_id else None
            return self._to_dict(user, doc)

    def set_status(self, username: str, status: str, admin_user: str = "admin") -> dict:
        """Activate or deactivate a doctor account in PostgreSQL."""
        norm_status = status.strip().title()
        if norm_status not in ("Active", "Inactive"):
            raise ValueError("Status must be either 'Active' or 'Inactive'.")
        return self.update_account(username, {"status": norm_status}, admin_user=admin_user)

    def get_account(self, username: str) -> Optional[dict]:
        """Get account details by username."""
        norm_username = username.strip().casefold()
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            user = session.execute(
                select(User).where(User.tenant_id == tenant_id, User.username == norm_username)
            ).scalar_one_or_none()
            if not user:
                return None
            doc = session.execute(
                select(Doctor).where(Doctor.tenant_id == tenant_id, Doctor.doctor_id == user.doctor_id)
            ).scalars().first() if user.doctor_id else None
            return self._to_dict(user, doc)

    def get_account_by_doctor_id(self, doctor_id: str) -> Optional[dict]:
        """Find account linked to a specific doctor ID."""
        norm_id = doctor_id.strip().casefold()
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            user = session.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.doctor_id.ilike(norm_id),
                )
            ).scalars().first()
            if not user:
                return None
            doc = session.execute(
                select(Doctor).where(Doctor.tenant_id == tenant_id, Doctor.doctor_id == user.doctor_id)
            ).scalars().first() if user.doctor_id else None
            return self._to_dict(user, doc)

    def list_accounts(self) -> list[dict]:
        """List all registered doctor accounts in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            users = session.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.role == "doctor",
                ).order_by(User.created_at.desc())
            ).scalars().all()

            results = []
            for u in users:
                doc = session.execute(
                    select(Doctor).where(Doctor.tenant_id == tenant_id, Doctor.doctor_id == u.doctor_id)
                ).scalars().first() if u.doctor_id else None
                results.append(self._to_dict(u, doc))
            return results

    def _to_dict(self, user: User, doc: Optional[Doctor]) -> dict:
        return {
            "username": user.username,
            "doctor_id": user.doctor_id or "",
            "doctor_name": doc.name if doc else (user.full_name or ""),
            "specialization": doc.specialization if doc else "",
            "email": user.email or "",
            "status": user.status or "Active",
            "must_change_password": user.must_change_password,
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "updated_at": user.updated_at.isoformat() if user.updated_at else "",
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }


# ---------------------------------------------------------------------------
# 6. PostgreSQL Audit Service
# ---------------------------------------------------------------------------

class PostgresAuditService:
    """PostgreSQL-backed audit logging service persisting immutable entries to audit_logs table."""

    def __init__(self, session_factory: sessionmaker[Session], max_memory_entries: int = 2000) -> None:
        self.session_factory = session_factory
        self.max_memory_entries = max_memory_entries
        self._lock = RLock()
        self._entries: list[dict] = []

    def record(
        self,
        user: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Optional[dict] = None,
    ) -> dict:
        """Record an immutable audit log entry in PostgreSQL."""
        now = datetime.now(timezone.utc)
        aid = f"AUD-{uuid4().hex[:12].upper()}"
        entry = {
            "id": aid,
            "timestamp": now.isoformat(),
            "user": user or "system",
            "action": action.upper().strip(),
            "entity_type": entity_type.lower().strip(),
            "entity_id": str(entity_id).strip(),
            "details": details or {},
        }

        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self.max_memory_entries:
                self._entries.pop(0)

        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            try:
                log_row = AuditLog(
                    tenant_id=tenant_id,
                    audit_id=aid,
                    timestamp=now,
                    user=user or "system",
                    action=action.upper().strip(),
                    entity_type=entity_type.lower().strip(),
                    entity_id=str(entity_id).strip(),
                    details=details or {},
                )
                session.add(log_row)
                session.commit()
            except Exception:
                session.rollback()

        return entry

    def get_logs(
        self,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Query audit logs with filtering and pagination from PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
            if action:
                stmt = stmt.where(AuditLog.action == action.strip().upper())
            if entity_type:
                stmt = stmt.where(AuditLog.entity_type == entity_type.strip().lower())
            if entity_id:
                stmt = stmt.where(AuditLog.entity_id == entity_id.strip())

            total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            rows = session.execute(
                stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
            ).scalars().all()

            logs = [
                {
                    "id": r.audit_id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else "",
                    "user": r.user,
                    "action": r.action,
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "details": r.details or {},
                }
                for r in rows
            ]
            return {
                "logs": logs,
                "total": total,
                "limit": limit,
                "offset": offset,
            }


# ---------------------------------------------------------------------------
# 7. PostgreSQL Payment Repository
# ---------------------------------------------------------------------------

class PostgresPaymentRepository:
    """PostgreSQL-backed payment boundary for tracking consultation billing."""

    def __init__(self, session_factory: sessionmaker[Session], upi_id: str = "") -> None:
        self.session_factory = session_factory
        self._upi_id = upi_id

    @property
    def upi_id(self) -> str:
        return self._upi_id

    def create_online_payment(
        self,
        amount: str,
        clinic_name: str = "Clinic",
        patient_name: str = "Patient",
        patient_phone: str = "",
        appointment_id: str = "",
        doctor_name: str = "",
        tenant_id: Optional[str] = None,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        upi_id: Optional[str] = None,
    ) -> dict:
        """Generate Razorpay payment link & direct UPI deep link, persisting Payment record in PostgreSQL."""
        effective_tenant = tenant_id or _resolve_tenant_id()
        resolved_key_id = key_id
        resolved_key_secret = key_secret
        resolved_upi = upi_id or self._upi_id

        # Look up clinic tenant credentials if not explicitly passed
        with self.session_factory() as session:
            clinic = session.execute(
                select(Clinic).where(Clinic.id == effective_tenant)
            ).scalar_one_or_none()
            if clinic:
                resolved_key_id = resolved_key_id or clinic.razorpay_key_id
                resolved_key_secret = resolved_key_secret or clinic.razorpay_key_secret
                resolved_upi = resolved_upi or clinic.upi_id or self._upi_id
                if not clinic_name or clinic_name == "Clinic":
                    clinic_name = clinic.name

        from ..services.razorpay_service import RazorpayService
        razorpay_svc = RazorpayService(
            default_key_id=resolved_key_id or "",
            default_key_secret=resolved_key_secret or "",
            default_upi_id=resolved_upi or "",
        )
        res = razorpay_svc.create_payment(
            amount=amount,
            clinic_name=clinic_name,
            patient_name=patient_name,
            patient_phone=patient_phone,
            appointment_id=appointment_id,
            doctor_name=doctor_name,
            key_id=resolved_key_id,
            key_secret=resolved_key_secret,
            upi_id=resolved_upi,
            tenant_id=effective_tenant,
        )

        # Persist to database
        try:
            with self.session_factory() as session:
                # Find linked appointment if exists
                appt_row = None
                if appointment_id:
                    appt_row = session.execute(
                        select(Appointment).where(
                            Appointment.tenant_id == effective_tenant,
                            or_(Appointment.token_no == str(appointment_id).strip(), Appointment.id == str(appointment_id).strip()),
                        )
                    ).scalars().first()

                payment_row = Payment(
                    tenant_id=effective_tenant,
                    payment_id=res["payment_id"],
                    appointment_id=appt_row.id if appt_row else None,
                    amount=str(res["amount"]),
                    currency=res.get("currency", "INR"),
                    payment_method="Razorpay / UPI",
                    payment_status="Pending",
                    gateway="Razorpay",
                    gateway_payload={
                        "payment_link_id": res.get("payment_link_id"),
                        "short_url": res.get("short_url"),
                        "upi_uri": res.get("upi_uri"),
                        "key_id": resolved_key_id,
                    },
                )
                session.add(payment_row)
                session.commit()
        except Exception as exc:
            logger.error("Failed to persist online payment row to DB: %s", exc)

        return res

    def mark_payment_status(
        self,
        payment_id: str,
        new_status: str = "Paid",
        transaction_reference: str = "",
    ) -> dict:
        """Mark payment and linked appointment as Paid in PostgreSQL."""
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            pay = session.execute(
                select(Payment).where(
                    Payment.tenant_id == tenant_id,
                    or_(Payment.payment_id == payment_id.strip(), Payment.id == payment_id.strip()),
                )
            ).scalars().first()

            appt = None
            if not pay:
                # Try finding appointment by token_no or id
                appt = session.execute(
                    select(Appointment).where(
                        Appointment.tenant_id == tenant_id,
                        or_(Appointment.token_no == payment_id.strip(), Appointment.id == payment_id.strip()),
                    )
                ).scalars().first()
                if appt:
                    pay = session.execute(
                        select(Payment).where(
                            Payment.tenant_id == tenant_id,
                            Payment.appointment_id == appt.id,
                        )
                    ).scalars().first()

            if not pay and not appt:
                return {"success": False, "status": "NOT_FOUND", "payment_id": payment_id}

            if pay:
                pay.payment_status = new_status
                if transaction_reference:
                    pay.transaction_reference = transaction_reference
                if new_status.casefold() in ("paid", "completed", "success"):
                    pay.paid_at = datetime.now(timezone.utc)

            # Update linked appointment if present
            if pay and pay.appointment_id and not appt:
                appt = session.execute(select(Appointment).where(Appointment.id == pay.appointment_id)).scalar_one_or_none()

            if appt:
                appt.payment_status = new_status
                if new_status.casefold() in ("paid", "completed", "success"):
                    appt.status = "Confirmed"

            session.commit()
            return {"success": True, "status": new_status, "payment_id": pay.payment_id if pay else payment_id}

    def verify_payment_status(self, payment_id: str) -> dict:
        tenant_id = _resolve_tenant_id()
        with self.session_factory() as session:
            pay = session.execute(
                select(Payment).where(
                    Payment.tenant_id == tenant_id,
                    or_(Payment.payment_id == payment_id.strip(), Payment.id == payment_id.strip()),
                )
            ).scalar_one_or_none()
            if pay:
                return {"success": True, "status": pay.payment_status, "payment_id": pay.payment_id}
            return {"success": False, "status": "NOT_FOUND", "payment_id": payment_id}

    def record_offline_payment(self, amount: str) -> dict:
        return {"success": True, "payment_method": "Offline", "payment_status": "Pending", "amount": amount}

    def get_payment_status(self, payment_id: str) -> dict:
        return self.verify_payment_status(payment_id)

    def generate_offline_upi_qr(self, amount: str, clinic_name: str, reference: str, output_dir: Path) -> dict:
        upi_id = (self._upi_id or "").strip()
        if not upi_id:
            return {
                "success": False,
                "error_code": "UPI_NOT_CONFIGURED",
                "message": "Online payment is not set up for this clinic. Please choose offline payment or contact the clinic.",
            }
        try:
            numeric_amount = Decimal(str(amount).replace(",", "").replace("₹", "").strip())
            if numeric_amount <= 0:
                raise InvalidOperation
            uri = "upi://pay?" + urlencode({"pa": upi_id, "pn": clinic_name, "am": f"{numeric_amount:.2f}", "cu": "INR", "tr": reference})
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / f"{reference}-upi.png"
            qrcode.make(uri).save(path)
            return {"success": True, "upi_id": upi_id, "amount": float(numeric_amount), "qr_path": str(path), "upi_uri": uri}
        except (InvalidOperation, ValueError, TypeError):
            return {"success": False, "error_code": "INVALID_AMOUNT", "message": "A valid consultation amount is required."}

