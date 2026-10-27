"""Contact domain model representing a unique phone / WhatsApp communication identity."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .clinic import Clinic
    from .patient import Patient


class Contact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Communication contact (e.g. WhatsApp phone number) owning one or more patient profiles."""

    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "phone", name="uq_contact_tenant_phone"),
        Index("ix_contact_tenant_phone", "tenant_id", "phone"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    clinic: Mapped[Optional["Clinic"]] = relationship("Clinic", back_populates="contacts")
    patients: Mapped[List["Patient"]] = relationship("Patient", back_populates="contact")

