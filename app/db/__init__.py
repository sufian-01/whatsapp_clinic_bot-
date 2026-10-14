"""Database package: SQLAlchemy 2.x foundation, session management, and domain models."""

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .models import (
    Appointment,
    AppointmentSlot,
    AuditLog,
    Clinic,
    Doctor,
    Invoice,
    Patient,
    Payment,
    Prescription,
    PrescriptionItem,
    User,
)
from .session import (
    get_db,
    get_engine,
    get_session_factory,
    is_db_configured,
    normalize_database_url,
    reset_db_state,
)

__all__ = [
    "Appointment",
    "AppointmentSlot",
    "AuditLog",
    "Base",
    "Clinic",
    "Doctor",
    "Invoice",
    "Patient",
    "Payment",
    "Prescription",
    "PrescriptionItem",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "User",
    "get_db",
    "get_engine",
    "get_session_factory",
    "is_db_configured",
    "normalize_database_url",
    "reset_db_state",
]

