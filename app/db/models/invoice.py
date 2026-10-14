"""Invoice domain model."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .appointment import Appointment
    from .clinic import Clinic
    from .patient import Patient
    from .payment import Payment


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Clinical consultation invoice generated for appointment billing."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_tenant_inv_no"),
        Index("ix_invoice_tenant_status", "tenant_id", "payment_status"),
    )

    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    clinic_id = synonym("tenant_id")

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    appointment_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), default="Offline", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), default="Pending", nullable=False, index=True)
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    qr_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    issued_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    clinic: Mapped[Optional["Clinic"]] = relationship("Clinic", back_populates="invoices")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="invoice")
    patient: Mapped["Patient"] = relationship("Patient", back_populates="invoices")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

