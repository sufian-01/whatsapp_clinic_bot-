"""Appointment domain model."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .clinic import Clinic
    from .doctor import Doctor
    from .invoice import Invoice
    from .patient import Patient
    from .payment import Payment
    from .prescription import Prescription
    from .slot import AppointmentSlot


class Appointment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Clinical consultation appointment record.

    Separates patient demographic identity from booking events.
    Enforces tenant-scoped concurrency uniqueness on (tenant_id, doctor_id, appointment_date, appointment_time).
    """

    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "token_no", name="uq_appointment_tenant_token_no"),
        UniqueConstraint(
            "doctor_id", "appointment_date", "appointment_time",
            name="uq_appointment_doctor_datetime",
        ),
        Index("ix_appointment_tenant_date_status", "tenant_id", "appointment_date", "booking_status"),
    )

    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    clinic_id = synonym("tenant_id")

    token_no: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("appointment_slots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    appointment_date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    appointment_time: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[str] = mapped_column(String(20), default="500", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), default="Offline", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), default="Pending", nullable=False, index=True)
    booking_status: Mapped[str] = mapped_column(String(50), default="Confirmed", nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    clinic: Mapped[Optional["Clinic"]] = relationship("Clinic", back_populates="appointments")
    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")
    slot: Mapped[Optional["AppointmentSlot"]] = relationship("AppointmentSlot", back_populates="appointment")
    prescription: Mapped[Optional["Prescription"]] = relationship("Prescription", back_populates="appointment", uselist=False)
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice", back_populates="appointment", uselist=False)
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="appointment", cascade="all, delete-orphan")
