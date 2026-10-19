"""Doctor domain model."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .appointment import Appointment
    from .clinic import Clinic
    from .prescription import Prescription
    from .slot import AppointmentSlot


class Doctor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Doctor / Clinician directory entity."""

    __tablename__ = "doctors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "doctor_id", name="uq_doctor_tenant_doctor_id"),
        Index("ix_doctor_tenant_name", "tenant_id", "name"),
        Index("ix_doctor_tenant_specialization", "tenant_id", "specialization"),
    )

    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    clinic_id = synonym("tenant_id")

    doctor_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    specialization: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    registration_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    available_days: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    end_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    consultation_fee: Mapped[str] = mapped_column(String(20), default="500", nullable=False)
    photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active", nullable=False, index=True)

    # Relationships
    clinic: Mapped[Optional["Clinic"]] = relationship("Clinic", back_populates="doctors")
    slots: Mapped[List["AppointmentSlot"]] = relationship("AppointmentSlot", back_populates="doctor", cascade="all, delete-orphan")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")
    prescriptions: Mapped[List["Prescription"]] = relationship("Prescription", back_populates="doctor", cascade="all, delete-orphan")

