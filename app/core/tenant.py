"""Centralized Multi-Tenant Context and Resolution Layer.

Provides:
- TenantContext data model.
- Async/thread-safe ContextVar tenant storage.
- Context manager for running code within an explicit tenant scope.
- FastAPI dependency for tenant resolution from authenticated user or request headers.
- Protection against client-supplied tenant ID spoofing.
"""

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
import logging
from typing import Any, Dict, Generator, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TenantContext:
    """Immutable representation of the resolved clinic/tenant context."""

    tenant_id: str
    clinic_name: str = ""
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    is_active: bool = True
    is_default: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


_CURRENT_TENANT: ContextVar[Optional[TenantContext]] = ContextVar("current_tenant", default=None)


def set_current_tenant(tenant: TenantContext) -> Token:
    """Set the active tenant context for the current execution context."""
    return _CURRENT_TENANT.set(tenant)


def reset_current_tenant(token: Token) -> None:
    """Reset the tenant context back to its previous state."""
    _CURRENT_TENANT.reset(token)


def get_current_tenant() -> Optional[TenantContext]:
    """Retrieve the active tenant context, or None if not set."""
    return _CURRENT_TENANT.get()


def require_current_tenant() -> TenantContext:
    """Retrieve the active tenant context, raising RuntimeError if missing.

    Ensures tenant-sensitive business services cannot run without an explicit tenant.
    """
    ctx = _CURRENT_TENANT.get()
    if ctx is None:
        raise RuntimeError("Tenant context is required for this operation, but none is active.")
    return ctx


@contextmanager
def tenant_scope(tenant: TenantContext | str) -> Generator[TenantContext, None, None]:
    """Context manager for running operations within an explicit tenant context."""
    if isinstance(tenant, str):
        tenant = TenantContext(tenant_id=tenant.strip())
    token = set_current_tenant(tenant)
    try:
        yield tenant
    finally:
        reset_current_tenant(token)


_TENANT_STATUS_CACHE: dict[str, str] = {}


def set_tenant_status(tenant_id: str, status_val: str) -> None:
    """Set cached tenant lifecycle status (ACTIVE, INACTIVE, SUSPENDED)."""
    _TENANT_STATUS_CACHE[str(tenant_id).strip()] = str(status_val).strip().upper()


def get_tenant_status(tenant_id: str) -> str:
    """Retrieve tenant lifecycle status (defaults to ACTIVE)."""
    clean_id = str(tenant_id).strip()
    return _TENANT_STATUS_CACHE.get(clean_id, "ACTIVE")


def reset_tenant_status_cache() -> None:
    """Clear tenant status cache."""
    _TENANT_STATUS_CACHE.clear()


async def resolve_tenant_context(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> TenantContext:
    """FastAPI Dependency: Resolves and enforces tenant context for incoming requests.

    Security Rules:
    1. If user is authenticated, the user's bound tenant_id is strictly authoritative.
       A client-supplied X-Tenant-ID header cannot override the authenticated user's tenant.
    2. Inactive or Suspended tenants are denied access (HTTP 403) for non-super-admins.
    3. Super Admin may explicitly operate across tenants via X-Tenant-ID.
    4. If unauthenticated, X-Tenant-ID header is used if provided.
    5. If neither is provided, falls back to the default single-clinic tenant for backward compatibility.
    """
    # 1. Check if user is authenticated (from session/cookie)
    auth_tenant_id = None
    auth_role = None
    try:
        from .auth import get_session
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token[7:].strip()
        elif not token:
            token = request.cookies.get("admin_session")

        if token:
            session = get_session(token)
            if session:
                auth_tenant_id = session.get("tenant_id") or session.get("clinic_id")
                auth_role = session.get("role")
    except Exception:
        auth_tenant_id = None
        auth_role = None

    settings = get_settings()

    # Rule 1: Authenticated user tenant resolution
    if auth_tenant_id or auth_role:
        from .rbac import UserRole
        is_super_admin = False
        if auth_role:
            try:
                is_super_admin = (UserRole.normalize(auth_role) == UserRole.SUPER_ADMIN)
            except Exception:
                is_super_admin = False

        if is_super_admin:
            if x_tenant_id and x_tenant_id.strip():
                # Super Admin explicitly operates on a specified tenant
                resolved_id = x_tenant_id.strip()
                t_status = get_tenant_status(resolved_id)
                ctx = TenantContext(
                    tenant_id=resolved_id,
                    clinic_name=f"Tenant {resolved_id}",
                    timezone=settings.clinic_timezone,
                    is_active=(t_status == "ACTIVE"),
                    is_default=(resolved_id == "default"),
                )
                set_current_tenant(ctx)
                return ctx
            else:
                # Super Admin without explicit tenant is strictly in platform scope (never defaults to a clinic)
                ctx = TenantContext(
                    tenant_id="platform",
                    clinic_name="Platform",
                    timezone=settings.clinic_timezone,
                    is_active=True,
                    is_default=False,
                )
                set_current_tenant(ctx)
                return ctx

        # For all other roles: Authenticated tenant is strictly authoritative
        if auth_tenant_id:
            if x_tenant_id and x_tenant_id.strip() != auth_tenant_id.strip():
                logger.warning(
                    "Cross-tenant access attempt blocked: user tenant '%s' vs client header '%s'",
                    auth_tenant_id, x_tenant_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden: You cannot access resources outside your assigned clinic tenant.",
                )
            resolved_id = auth_tenant_id.strip()
            t_status = get_tenant_status(resolved_id)
            if t_status in ("INACTIVE", "SUSPENDED"):
                logger.warning("Access denied: Tenant '%s' is %s", resolved_id, t_status)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Clinic tenant is {t_status.lower()}. Please contact clinic administration.",
                )

            ctx = TenantContext(
                tenant_id=resolved_id,
                clinic_name=settings.clinic_name,
                timezone=settings.clinic_timezone,
                is_active=True,
                is_default=(resolved_id == "default"),
            )
            set_current_tenant(ctx)
            return ctx

    # Rule 2: Unauthenticated client with X-Tenant-ID header
    if x_tenant_id and x_tenant_id.strip():
        resolved_id = x_tenant_id.strip()
        t_status = get_tenant_status(resolved_id)
        if t_status in ("INACTIVE", "SUSPENDED"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Clinic tenant is {t_status.lower()}.",
            )
        ctx = TenantContext(
            tenant_id=resolved_id,
            clinic_name=settings.clinic_name,
            timezone=settings.clinic_timezone,
            is_active=True,
            is_default=False,
        )
        set_current_tenant(ctx)
        return ctx

    # Rule 3: Backward-compatibility default single-clinic tenant
    ctx = TenantContext(
        tenant_id="default",
        clinic_name=settings.clinic_name,
        timezone=settings.clinic_timezone,
        is_active=True,
        is_default=True,
    )
    set_current_tenant(ctx)
    return ctx


async def require_tenant(
    tenant: TenantContext = Depends(resolve_tenant_context),
) -> TenantContext:
    """FastAPI Dependency: Requires an active, validated clinic tenant context."""
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinic tenant is inactive or suspended. Please contact clinic administration.",
        )
    if tenant.tenant_id == "platform":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation requires an explicit clinic tenant context. Super Admin must specify X-Tenant-ID header.",
        )
    return tenant

