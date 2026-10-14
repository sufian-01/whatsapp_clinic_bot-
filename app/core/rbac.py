"""Role-Based Access Control (RBAC) and Permissions Architecture.

Defines target SaaS roles, discrete permissions, the explicit role-permission matrix,
and centralized FastAPI authorization dependencies.
"""

from enum import Enum
import logging
from typing import Callable, Iterable, Optional, Set, Union

from fastapi import Depends, HTTPException, status

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Target SaaS Roles
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    """Target roles for the multi-tenant clinic SaaS platform."""

    SUPER_ADMIN = "SUPER_ADMIN"
    TENANT_ADMIN = "TENANT_ADMIN"
    DOCTOR = "DOCTOR"
    RECEPTIONIST = "RECEPTIONIST"
    STAFF = "STAFF"
    PATIENT = "PATIENT"

    @classmethod
    def normalize(cls, role_val: Union[str, "UserRole"]) -> "UserRole":
        """Normalize case-insensitive or legacy role strings to UserRole enum.

        Maps legacy 'admin' -> TENANT_ADMIN, 'doctor' -> DOCTOR, etc.
        """
        if isinstance(role_val, cls):
            return role_val

        clean = str(role_val).strip().casefold()
        mapping = {
            "super_admin": cls.SUPER_ADMIN,
            "superadmin": cls.SUPER_ADMIN,
            "super": cls.SUPER_ADMIN,
            "admin": cls.TENANT_ADMIN,
            "tenant_admin": cls.TENANT_ADMIN,
            "tenantadmin": cls.TENANT_ADMIN,
            "doctor": cls.DOCTOR,
            "physician": cls.DOCTOR,
            "receptionist": cls.RECEPTIONIST,
            "reception": cls.RECEPTIONIST,
            "staff": cls.STAFF,
            "patient": cls.PATIENT,
        }
        if clean in mapping:
            return mapping[clean]

        # Check direct value match
        for item in cls:
            if item.value.casefold() == clean:
                return item

        raise ValueError(
            f"Invalid role: '{role_val}'. Allowed roles: {[r.value for r in cls]}"
        )


# ---------------------------------------------------------------------------
# 2. Permissions & Capabilities
# ---------------------------------------------------------------------------

class Permission(str, Enum):
    """Discrete system permissions."""

    # Platform (Super Admin)
    PLATFORM_MANAGE = "platform:manage"
    PLATFORM_CONFIG = "platform:config"
    PLATFORM_AUDIT = "platform:audit"

    # Clinic / Tenant Admin
    TENANT_CONFIG = "tenant:config"
    USER_MANAGE = "user:manage"
    DOCTOR_MANAGE = "doctor:manage"
    CLINIC_AUDIT_VIEW = "clinic:audit_view"
    KNOWLEDGE_UPLOAD = "knowledge:upload"

    # Clinical / Operations
    CLINICAL_OPERATION = "clinical:operation"
    PRESCRIPTION_MANAGE = "prescription:manage"
    APPOINTMENT_MANAGE = "appointment:manage"
    SLOT_MANAGE = "slot:manage"
    PATIENT_MANAGE = "patient:manage"
    BILLING_MANAGE = "billing:manage"

    # Patient Self-Service
    PATIENT_SELF_SERVICE = "patient:self_service"


# ---------------------------------------------------------------------------
# 3. Role-Permission Matrix
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    # Platform Super Admin: Explicit platform-level management.
    # Note: Does NOT get unrestricted clinical access by default (principle of least privilege)
    UserRole.SUPER_ADMIN: frozenset({
        Permission.PLATFORM_MANAGE,
        Permission.PLATFORM_CONFIG,
        Permission.PLATFORM_AUDIT,
        Permission.KNOWLEDGE_UPLOAD,
    }),

    # Tenant / Clinic Admin: Full administration within their clinic
    UserRole.TENANT_ADMIN: frozenset({
        Permission.TENANT_CONFIG,
        Permission.USER_MANAGE,
        Permission.DOCTOR_MANAGE,
        Permission.PATIENT_MANAGE,
        Permission.APPOINTMENT_MANAGE,
        Permission.SLOT_MANAGE,
        Permission.PRESCRIPTION_MANAGE,
        Permission.BILLING_MANAGE,
        Permission.CLINIC_AUDIT_VIEW,
        Permission.KNOWLEDGE_UPLOAD,
        Permission.CLINICAL_OPERATION,
    }),

    # Clinician / Doctor: Clinical workflow, own prescriptions, slots, and appointments
    UserRole.DOCTOR: frozenset({
        Permission.CLINICAL_OPERATION,
        Permission.PRESCRIPTION_MANAGE,
        Permission.APPOINTMENT_MANAGE,
        Permission.SLOT_MANAGE,
    }),

    # Receptionist: Patient check-in, bookings, slots, and payment collection
    UserRole.RECEPTIONIST: frozenset({
        Permission.PATIENT_MANAGE,
        Permission.APPOINTMENT_MANAGE,
        Permission.SLOT_MANAGE,
        Permission.BILLING_MANAGE,
    }),

    # Basic Operations Staff: Limited booking & patient lookups
    UserRole.STAFF: frozenset({
        Permission.PATIENT_MANAGE,
        Permission.APPOINTMENT_MANAGE,
    }),

    # Patient: Portal self-service
    UserRole.PATIENT: frozenset({
        Permission.PATIENT_SELF_SERVICE,
    }),
}


def get_role_permissions(role: Union[str, UserRole]) -> frozenset[Permission]:
    """Return the set of permissions assigned to a role."""
    norm_role = UserRole.normalize(role)
    return ROLE_PERMISSIONS.get(norm_role, frozenset())


def has_permission(role: Union[str, UserRole], permission: Permission) -> bool:
    """Return True if role has the specified permission."""
    try:
        norm_role = UserRole.normalize(role)
        return permission in ROLE_PERMISSIONS.get(norm_role, frozenset())
    except ValueError:
        return False


def has_any_permission(role: Union[str, UserRole], permissions: Iterable[Permission]) -> bool:
    """Return True if role has at least one of the specified permissions."""
    try:
        norm_role = UserRole.normalize(role)
        perms = ROLE_PERMISSIONS.get(norm_role, frozenset())
        return any(p in perms for p in permissions)
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# 4. Centralized FastAPI Authorization Dependencies
# ---------------------------------------------------------------------------

from .auth import get_current_user  # deferred import to avoid cycles


async def require_authenticated_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """FastAPI dependency: Requires any authenticated and active user."""
    # Status / is_active check
    if current_user.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive or suspended. Please contact clinic administration.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    status_str = str(current_user.get("status", "")).strip().casefold()
    if status_str in ("inactive", "suspended"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive or suspended. Please contact clinic administration.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_role(*allowed_roles: Union[str, UserRole]) -> Callable:
    """FastAPI Dependency factory: Require user to have one of the specified roles."""
    normalized_allowed = {UserRole.normalize(r) for r in allowed_roles}

    async def _role_checker(
        current_user: dict = Depends(require_authenticated_user),
    ) -> dict:
        user_role_str = current_user.get("role", "")
        try:
            user_role = UserRole.normalize(user_role_str)
        except ValueError:
            logger.warning("User '%s' has unparseable role '%s'", current_user.get("username"), user_role_str)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Invalid or unrecognized account role.",
            )

        if user_role not in normalized_allowed:
            allowed_names = [r.value for r in sorted(normalized_allowed, key=lambda x: x.value)]
            logger.warning(
                "Access denied for user '%s': role '%s' not in required %s",
                current_user.get("username"),
                user_role.value,
                allowed_names,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Required role in {allowed_names}.",
            )
        return current_user

    return _role_checker


def require_permission(required_permission: Permission) -> Callable:
    """FastAPI Dependency factory: Require user to possess a specific permission."""

    async def _perm_checker(
        current_user: dict = Depends(require_authenticated_user),
    ) -> dict:
        user_role_str = current_user.get("role", "")
        if not has_permission(user_role_str, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Permission '{required_permission.value}' required.",
            )
        return current_user

    return _perm_checker


# ---------------------------------------------------------------------------
# 5. Pre-Configured Convenient Role Dependencies
# ---------------------------------------------------------------------------

require_super_admin = require_role(UserRole.SUPER_ADMIN)
require_tenant_admin = require_role(UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN)
require_doctor = require_role(UserRole.DOCTOR)
require_receptionist = require_role(UserRole.RECEPTIONIST, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN)
require_staff = require_role(UserRole.STAFF, UserRole.RECEPTIONIST, UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN)
require_patient = require_role(UserRole.PATIENT)
require_admin_or_doctor = require_role(UserRole.TENANT_ADMIN, UserRole.SUPER_ADMIN, UserRole.DOCTOR)
require_clinical_or_admin = require_admin_or_doctor

