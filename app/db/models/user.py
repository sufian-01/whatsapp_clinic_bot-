"""User / Staff / Doctor account domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from ..base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .clinic import Clinic


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account for staff, clinicians, and administrators."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),
        Index("ix_user_tenant_role", "tenant_id", "role"),
    )

    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    clinic_id = synonym("tenant_id")

    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="doctor", nullable=False, index=True)
    doctor_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Active", nullable=False, index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at = synonym("last_login")

    @property
    def is_active(self) -> bool:
        """Boolean flag indicating whether the account is active."""
        return (self.status or "").strip().casefold() == "active"

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self.status = "Active" if value else "Inactive"

    def set_role(self, new_role: str) -> None:
        """Set role with strict validation against UserRole enum."""
        from ...core.rbac import UserRole
        self.role = UserRole.normalize(new_role).value

    # Relationship to clinic / tenant
    clinic: Mapped[Optional["Clinic"]] = relationship("Clinic", back_populates="users")

