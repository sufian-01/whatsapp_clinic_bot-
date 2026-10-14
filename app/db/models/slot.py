"""Appointment slot domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .appointment import Appointment
    from .clinic import Clinic
    from .doctor import Doctor


class AppointmentSlot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific doctor time slot available for booking.

    Enforces tenant-scoped database-level concurrency protection through a unique constraint
    on (tenant_id, doctor_id, date, start_time) to prevent double-booking.
    """

    __tablename__ = "appointment_slots"
    __table_args__ = (
        UniqueConstraint("doctor_id", "date", "start_time", name="uq_slot_doctor_date_start_time"),
        UniqueConstraint("tenant_id", "slot_id", name="uq_slot_tenant_slot_id"),
        Index("ix_slot_tenant_date_status", "tenant_id", "date", "status"),
    )

    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    clinic_id = synonym("tenant_id")

    slot_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    doctor_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    start_time: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # HH:MM
    end_time: Mapped[str] = mapped_column(String(20), nullable=False)  # HH:MM
    status: Mapped[str] = mapped_column(String(50), default="available", nullable=False, index=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    booked_patient_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    booked_token_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # Relationships
    clinic: Mapped[Optional["Clinic"]] = relationship("Clinic", back_populates="slots")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="slots")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="slot", uselist=False)
