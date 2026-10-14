"""Tenant-Scoped Repository Pattern for PostgreSQL persistence.

Guarantees that database queries are strictly partitioned by tenant_id,
preventing any possibility of cross-tenant data leakage.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
import uuid

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..db.models import (
    Appointment,
    AppointmentSlot,
    AuditLog,
    Doctor,
    Invoice,
    Patient,
    Payment,
    Prescription,
    PrescriptionItem,
    User,
)

T = TypeVar("T")


class TenantScopedRepository(Generic[T]):
    """Base repository enforcing tenant isolation across all database operations."""

    def __init__(self, session: Session, tenant_id: str, model_cls: Type[T]) -> None:
        if not tenant_id or not str(tenant_id).strip():
            raise ValueError("TenantScopedRepository requires a valid, non-empty tenant_id.")
        self.session = session
        self.tenant_id = str(tenant_id).strip()
        self.model_cls = model_cls

    def _base_query(self):
        """Construct a SELECT statement pre-filtered by the current tenant_id."""
        return select(self.model_cls).where(self.model_cls.tenant_id == self.tenant_id)


class TenantPatientRepository(TenantScopedRepository[Patient]):
    """Tenant-scoped repository for Patient entities."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, tenant_id, Patient)

    def get(self, identifier: str) -> Optional[Patient]:
        """Fetch patient by internal ID or patient_id strictly within the current tenant."""
        stmt = self._base_query().where(
            (Patient.id == identifier) | (Patient.patient_id == identifier)
        )
        return self.session.execute(stmt).scalars().first()

    def get_by_phone(self, phone: str) -> List[Patient]:
        """Find patients by phone strictly within the current tenant."""
        stmt = self._base_query().where(Patient.phone == phone.strip())
        return list(self.session.execute(stmt).scalars().all())

    def list(self, limit: int = 50, offset: int = 0) -> List[Patient]:
        """List patients within the current tenant."""
        stmt = self._base_query().order_by(Patient.name).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars().all())

    def create(
        self,
        name: str,
        phone: str,
        patient_id: Optional[str] = None,
        email: str = "",
        age: str = "",
        gender: str = "",
        address: str = "",
        medical_history: str = "",
    ) -> Patient:
        """Create a new patient bound strictly to the current tenant."""
        pid = patient_id or f"PAT-{uuid.uuid4().hex[:12].upper()}"
        patient = Patient(
            tenant_id=self.tenant_id,
            patient_id=pid,
            name=name.strip(),
            phone=phone.strip(),
            email=email.strip() or None,
            age=age.strip() or None,
            gender=gender.strip() or None,
            address=address.strip() or None,
            medical_history=medical_history.strip() or None,
        )
        self.session.add(patient)
        self.session.flush()
        return patient


class TenantDoctorRepository(TenantScopedRepository[Doctor]):
    """Tenant-scoped repository for Doctor entities."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, tenant_id, Doctor)

    def get(self, identifier: str) -> Optional[Doctor]:
        """Fetch doctor by internal ID or doctor_id strictly within the current tenant."""
        stmt = self._base_query().where(
            (Doctor.id == identifier) | (Doctor.doctor_id == identifier)
        )
        return self.session.execute(stmt).scalars().first()

    def list_active(self) -> List[Doctor]:
        """List active doctors within the current tenant."""
        stmt = self._base_query().where(Doctor.status == "Active").order_by(Doctor.name)
        return list(self.session.execute(stmt).scalars().all())

    def create(
        self,
        name: str,
        specialization: str,
        doctor_id: Optional[str] = None,
        qualification: str = "",
        registration_no: str = "",
        phone: str = "",
        email: str = "",
        consultation_fee: str = "500",
    ) -> Doctor:
        """Create a new doctor bound strictly to the current tenant."""
        did = doctor_id or f"DOC-{uuid.uuid4().hex[:6].upper()}"
        doctor = Doctor(
            tenant_id=self.tenant_id,
            doctor_id=did,
            name=name.strip(),
            specialization=specialization.strip(),
            qualification=qualification.strip() or None,
            registration_no=registration_no.strip() or None,
            phone=phone.strip() or None,
            email=email.strip() or None,
            consultation_fee=consultation_fee,
            status="Active",
        )
        self.session.add(doctor)
        self.session.flush()
        return doctor


class TenantSlotRepository(TenantScopedRepository[AppointmentSlot]):
    """Tenant-scoped repository for AppointmentSlot entities."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, tenant_id, AppointmentSlot)

    def get(self, identifier: str) -> Optional[AppointmentSlot]:
        stmt = self._base_query().where(
            (AppointmentSlot.id == identifier) | (AppointmentSlot.slot_id == identifier)
        )
        return self.session.execute(stmt).scalars().first()

    def list_available(self, doctor_id: str, date: str) -> List[AppointmentSlot]:
        stmt = self._base_query().where(
            AppointmentSlot.doctor_id == doctor_id,
            AppointmentSlot.date == date,
            AppointmentSlot.status == "available",
        ).order_by(AppointmentSlot.start_time)
        return list(self.session.execute(stmt).scalars().all())

    def create(
        self,
        doctor_id: str,
        date: str,
        start_time: str,
        end_time: str,
        slot_id: Optional[str] = None,
    ) -> AppointmentSlot:
        sid = slot_id or f"SLT-{uuid.uuid4().hex[:8].upper()}"
        slot = AppointmentSlot(
            tenant_id=self.tenant_id,
            slot_id=sid,
            doctor_id=doctor_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            status="available",
        )
        self.session.add(slot)
        self.session.flush()
        return slot


class TenantAppointmentRepository(TenantScopedRepository[Appointment]):
    """Tenant-scoped repository for Appointment entities."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, tenant_id, Appointment)

    def get(self, identifier: str) -> Optional[Appointment]:
        stmt = self._base_query().where(
            (Appointment.id == identifier) | (Appointment.token_no == identifier)
        )
        return self.session.execute(stmt).scalars().first()

    def list_by_doctor_and_date(self, doctor_id: str, date: str) -> List[Appointment]:
        stmt = self._base_query().where(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == date,
        ).order_by(Appointment.appointment_time)
        return list(self.session.execute(stmt).scalars().all())

    def create(
        self,
        patient_id: str,
        doctor_id: str,
        appointment_date: str,
        appointment_time: str,
        token_no: Optional[str] = None,
        slot_id: Optional[str] = None,
        amount: str = "500",
        payment_method: str = "Offline",
        payment_status: str = "Pending",
        booking_status: str = "Confirmed",
    ) -> Appointment:
        tkn = token_no or f"TKN-{uuid.uuid4().hex[:6].upper()}"
        appt = Appointment(
            tenant_id=self.tenant_id,
            token_no=tkn,
            patient_id=patient_id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            amount=amount,
            payment_method=payment_method,
            payment_status=payment_status,
            booking_status=booking_status,
        )
        self.session.add(appt)
        self.session.flush()
        return appt


class TenantPrescriptionRepository(TenantScopedRepository[Prescription]):
    """Tenant-scoped repository for Prescription entities."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, tenant_id, Prescription)

    def get(self, identifier: str) -> Optional[Prescription]:
        stmt = self._base_query().where(
            (Prescription.id == identifier) | (Prescription.prescription_id == identifier)
        )
        return self.session.execute(stmt).scalars().first()

    def list_by_patient(self, patient_id: str) -> List[Prescription]:
        stmt = self._base_query().where(Prescription.patient_id == patient_id).order_by(Prescription.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def create(
        self,
        patient_id: str,
        doctor_id: str,
        date: str,
        diagnosis: str,
        prescription_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
        clinical_notes: str = "",
        status: str = "draft",
        medicines: Optional[List[Dict[str, Any]]] = None,
    ) -> Prescription:
        rx_id = prescription_id or f"RX-{uuid.uuid4().hex[:10].upper()}"
        rx = Prescription(
            tenant_id=self.tenant_id,
            prescription_id=rx_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_id=appointment_id,
            date=date,
            diagnosis=diagnosis,
            clinical_notes=clinical_notes or None,
            status=status,
        )
        if medicines:
            for idx, med in enumerate(medicines, start=1):
                item = PrescriptionItem(
                    prescription_id=rx.id,
                    order_index=idx,
                    name=med.get("name", ""),
                    strength=med.get("strength"),
                    dosage=med.get("dosage"),
                    frequency=med.get("frequency"),
                    duration=med.get("duration"),
                    instructions=med.get("instructions"),
                )
                rx.items.append(item)
        self.session.add(rx)
        self.session.flush()
        return rx


class TenantInvoiceRepository(TenantScopedRepository[Invoice]):
    """Tenant-scoped repository for Invoice entities."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, tenant_id, Invoice)

    def get(self, identifier: str) -> Optional[Invoice]:
        stmt = self._base_query().where(
            (Invoice.id == identifier) | (Invoice.invoice_number == identifier)
        )
        return self.session.execute(stmt).scalars().first()

    def create(
        self,
        patient_id: str,
        amount: str,
        invoice_number: Optional[str] = None,
        appointment_id: Optional[str] = None,
        payment_method: str = "Offline",
        payment_status: str = "Pending",
        upi_id: str = "",
    ) -> Invoice:
        inv_no = invoice_number or f"INV-{uuid.uuid4().hex[:10].upper()}"
        inv = Invoice(
            tenant_id=self.tenant_id,
            invoice_number=inv_no,
            patient_id=patient_id,
            appointment_id=appointment_id,
            amount=amount,
            payment_method=payment_method,
            payment_status=payment_status,
            upi_id=upi_id or None,
        )
        self.session.add(inv)
        self.session.flush()
        return inv


class TenantPaymentRepository(TenantScopedRepository[Payment]):
    """Tenant-scoped repository for Payment entities."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, tenant_id, Payment)

    def get(self, identifier: str) -> Optional[Payment]:
        stmt = self._base_query().where(
            (Payment.id == identifier) | (Payment.payment_id == identifier)
        )
        return self.session.execute(stmt).scalars().first()

    def create(
        self,
        amount: str,
        payment_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
        payment_method: str = "Offline",
        payment_status: str = "Pending",
        transaction_reference: str = "",
    ) -> Payment:
        pid = payment_id or f"PAY-{uuid.uuid4().hex[:10].upper()}"
        pay = Payment(
            tenant_id=self.tenant_id,
            payment_id=pid,
            appointment_id=appointment_id,
            invoice_id=invoice_id,
            amount=amount,
            payment_method=payment_method,
            payment_status=payment_status,
            transaction_reference=transaction_reference or None,
        )
        self.session.add(pay)
        self.session.flush()
        return pay


class TenantAuditRepository(TenantScopedRepository[AuditLog]):
    """Tenant-scoped repository for AuditLog entities."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, tenant_id, AuditLog)

    def record(
        self,
        user: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None,
        audit_id: Optional[str] = None,
    ) -> AuditLog:
        aid = audit_id or f"AUD-{uuid.uuid4().hex[:10].upper()}"
        entry = AuditLog(
            tenant_id=self.tenant_id,
            audit_id=aid,
            timestamp=datetime.now(timezone.utc),
            user=user,
            action=action.upper(),
            entity_type=entity_type.lower(),
            entity_id=str(entity_id),
            details=details or {},
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def list(
        self,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AuditLog]:
        stmt = self._base_query()
        if action:
            stmt = stmt.where(AuditLog.action == action.upper())
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type.lower())
        stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars().all())


class TenantUserRepository(TenantScopedRepository[User]):
    """Tenant-scoped repository for User entities (staff, clinicians, clinic admins)."""

    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, tenant_id, User)

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = self._base_query().where(User.username == username.strip().casefold())
        return self.session.execute(stmt).scalars().first()

    def get(self, identifier: str) -> Optional[User]:
        stmt = self._base_query().where(
            (User.id == identifier) | (User.username == identifier.strip().casefold())
        )
        return self.session.execute(stmt).scalars().first()

    def list_by_role(self, role: str) -> List[User]:
        stmt = self._base_query().where(User.role == role.upper()).order_by(User.username)
        return list(self.session.execute(stmt).scalars().all())

    def create(
        self,
        username: str,
        password_hash: str,
        role: str = "STAFF",
        full_name: str = "",
        email: str = "",
        doctor_id: Optional[str] = None,
    ) -> User:
        user = User(
            tenant_id=self.tenant_id,
            username=username.strip().casefold(),
            password_hash=password_hash,
            role=role.upper(),
            full_name=full_name.strip() or None,
            email=email.strip() or None,
            doctor_id=doctor_id,
            is_active=True,
        )
        self.session.add(user)
        self.session.flush()
        return user


