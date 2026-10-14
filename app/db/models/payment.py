"""Payment transaction domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .appointment import Appointment
    from .clinic import Clinic
    from .invoice import Invoice


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Payment transaction record associated with an appointment and invoice."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "payment_id", name="uq_payment_tenant_payment_id"),
        Index("ix_payment_tenant_status", "tenant_id", "payment_status"),
    )

    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    clinic_id = synonym("tenant_id")

    payment_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    appointment_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), default="Offline", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), default="Pending", nullable=False, index=True)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    gateway: Mapped[Optional[str]] = mapped_column(String(50), default="Offline", nullable=True)
    gateway_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    clinic: Mapped[Optional["Clinic"]] = relationship("Clinic", back_populates="payments")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="payments")
    invoice: Mapped[Optional["Invoice"]] = relationship("Invoice", back_populates="payments")

