"""WhatsApp conversations and messages domain models."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .clinic import Clinic
    from .patient import Patient


class WhatsAppConversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a WhatsApp chat thread between a clinic/tenant and a patient/phone."""

    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "phone_number", name="uq_whatsapp_conv_tenant_phone"),
        Index("ix_whatsapp_conv_tenant_phone", "tenant_id", "phone_number"),
        Index("ix_whatsapp_conv_patient_id", "patient_id"),
        Index("ix_whatsapp_conv_last_message", "tenant_id", "last_message_at"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clinic_id = synonym("tenant_id")

    phone_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    wa_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    profile_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    patient_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(50), default="whatsapp", nullable=False)
    session_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="whatsapp_conversations")
    patient: Mapped[Optional["Patient"]] = relationship("Patient", back_populates="whatsapp_conversations")
    messages: Mapped[List["WhatsAppMessage"]] = relationship(
        "WhatsAppMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="WhatsAppMessage.created_at.asc()",
    )


class WhatsAppMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an inbound or outbound WhatsApp message with lifecycle status."""

    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        UniqueConstraint("tenant_id", "whatsapp_message_id", name="uq_whatsapp_msg_tenant_wamid"),
        Index("ix_whatsapp_msg_tenant_wamid", "tenant_id", "whatsapp_message_id"),
        Index("ix_whatsapp_msg_conv_created", "conversation_id", "created_at"),
        Index("ix_whatsapp_msg_tenant_status", "tenant_id", "status"),
        Index("ix_whatsapp_msg_phone", "tenant_id", "phone_number"),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clinic_id = synonym("tenant_id")

    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    whatsapp_message_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    phone_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # 'inbound' | 'outbound'
    message_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)  # 'text', 'interactive', 'template', etc.
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="received", nullable=False, index=True)  # 'received', 'sent', 'delivered', 'read', 'failed'
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="whatsapp_messages")
    conversation: Mapped[Optional["WhatsAppConversation"]] = relationship(
        "WhatsAppConversation", back_populates="messages"
    )

