from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .appointment import Appointment
    from .audit import AuditLog
    from .doctor import Doctor
    from .invoice import Invoice
    from .patient import Patient
    from .payment import Payment
    from .prescription import Prescription
    from .slot import AppointmentSlot
    from .user import User
    from .whatsapp import WhatsAppConversation, WhatsAppMessage


class Clinic(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an independent healthcare clinic/hospital tenant."""

    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    upi_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    razorpay_key_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    razorpay_key_secret: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    working_days: Mapped[Optional[str]] = mapped_column(String(255), default="Monday - Friday", nullable=True)
    working_hours: Mapped[Optional[str]] = mapped_column(String(100), default="09:00 - 17:00", nullable=True)
    appointment_duration: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    booking_settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rag_config_status: Mapped[str] = mapped_column(String(50), default="CONFIGURED", nullable=False)
    channel_config_status: Mapped[str] = mapped_column(String(50), default="CONFIGURED", nullable=False)

    # WhatsApp Channel Multi-Tenant Routing
    whatsapp_phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    whatsapp_phone_number_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    whatsapp_waba_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # SaaS Subscription & Granular Feature Flags
    subscription_plan: Mapped[str] = mapped_column(String(50), default="STARTER", nullable=False)
    subscription_status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    feature_flags: Mapped[Optional[str]] = mapped_column(Text, default="{}", nullable=True)

    def activate(self) -> None:
        """Activate clinic tenant."""
        self.status = "ACTIVE"
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate clinic tenant."""
        self.status = "INACTIVE"
        self.is_active = False

    def suspend(self) -> None:
        """Suspend clinic tenant."""
        self.status = "SUSPENDED"
        self.is_active = False

    # Relationships to tenant-owned entities
    users: Mapped[List["User"]] = relationship("User", back_populates="clinic", cascade="all, delete-orphan")
    doctors: Mapped[List["Doctor"]] = relationship("Doctor", back_populates="clinic", cascade="all, delete-orphan")
    patients: Mapped[List["Patient"]] = relationship("Patient", back_populates="clinic", cascade="all, delete-orphan")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="clinic", cascade="all, delete-orphan")
    slots: Mapped[List["AppointmentSlot"]] = relationship("AppointmentSlot", back_populates="clinic", cascade="all, delete-orphan")
    prescriptions: Mapped[List["Prescription"]] = relationship("Prescription", back_populates="clinic", cascade="all, delete-orphan")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="clinic", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="clinic", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="clinic", cascade="all, delete-orphan")
    whatsapp_conversations: Mapped[List["WhatsAppConversation"]] = relationship("WhatsAppConversation", back_populates="clinic", cascade="all, delete-orphan")
    whatsapp_messages: Mapped[List["WhatsAppMessage"]] = relationship("WhatsAppMessage", back_populates="clinic", cascade="all, delete-orphan")

