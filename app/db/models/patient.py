"""Patient domain model."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .appointment import Appointment
    from .clinic import Clinic
    from .invoice import Invoice
    from .prescription import Prescription
    from .whatsapp import WhatsAppConversation


class Patient(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Patient demographic and medical profile entity."""

    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "patient_id", name="uq_patient_tenant_patient_id"),
        Index("ix_patient_tenant_phone", "tenant_id", "phone"),
        Index("ix_patient_tenant_name", "tenant_id", "name"),
    )

    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    clinic_id = synonym("tenant_id")

    patient_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    age: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medical_history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active", nullable=False, index=True)

    # Relationships
    clinic: Mapped[Optional["Clinic"]] = relationship("Clinic", back_populates="patients")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    prescriptions: Mapped[List["Prescription"]] = relationship("Prescription", back_populates="patient", cascade="all, delete-orphan")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="patient", cascade="all, delete-orphan")
    whatsapp_conversations: Mapped[List["WhatsAppConversation"]] = relationship("WhatsAppConversation", back_populates="patient")

