"""FastAPI Super Admin & Platform Tenant Management Router.

Endpoints for managing multi-tenant clinics, facility lifecycles, and tenant administrators.
Strictly protected by `require_super_admin`.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field

from ..core.auth import (
    check_account_lockout,
    clear_failed_login,
    create_session,
    record_failed_login,
    verify_password,
)
from ..core.config import Settings
from ..core.rbac import require_super_admin
from ..services.tenant_management_service import TenantManagementService


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class SuperAdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class SuperAdminLoginResponse(BaseModel):
    token: str
    username: str
    role: str = "SUPER_ADMIN"
    tenant_id: str = "platform"


class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = ""
    id: Optional[str] = None
    logo: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    website: Optional[str] = ""
    address: Optional[str] = ""
    timezone: Optional[str] = "Asia/Kolkata"
    currency: Optional[str] = "INR"
    working_days: Optional[str] = "Monday - Friday"
    working_hours: Optional[str] = "09:00 - 17:00"
    appointment_duration: Optional[int] = 30
    booking_settings: Optional[str] = "{}"
    status: Optional[str] = "ACTIVE"
    whatsapp_phone_number: Optional[str] = ""
    whatsapp_phone_number_id: Optional[str] = ""
    whatsapp_waba_id: Optional[str] = ""
    subscription_plan: Optional[str] = "STARTER"
    subscription_status: Optional[str] = "ACTIVE"
    subscription_expires_at: Optional[str] = None
    feature_flags: Optional[Dict[str, bool]] = None


class TenantUpdateRequest(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    logo: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    working_days: Optional[str] = None
    working_hours: Optional[str] = None
    appointment_duration: Optional[int] = None
    booking_settings: Optional[str] = None
    status: Optional[str] = None
    whatsapp_phone_number: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_waba_id: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_expires_at: Optional[str] = None
    feature_flags: Optional[Dict[str, bool]] = None


class TenantFeaturesUpdateRequest(BaseModel):
    feature_flags: Dict[str, bool]


class TenantSubscriptionUpdateRequest(BaseModel):
    subscription_plan: str
    subscription_status: Optional[str] = "ACTIVE"
    subscription_expires_at: Optional[str] = None


class TenantSuspendRequest(BaseModel):
    reason: Optional[str] = "Administrative suspension"


class TenantAdminCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = ""
    email: Optional[str] = ""



# ---------------------------------------------------------------------------
# Router Factory
# ---------------------------------------------------------------------------

def create_super_admin_router(
    service: TenantManagementService,
    settings: Settings,
) -> APIRouter:
    router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])

    # -----------------------------------------------------------------------
    # AUTHENTICATION
    # -----------------------------------------------------------------------
    @router.post("/auth/login", response_model=SuperAdminLoginResponse)
    async def super_admin_login(credentials: SuperAdminLoginRequest, response: Response):
        """Authenticate platform Super Admin with lockout protection."""
        is_locked, secs = check_account_lockout(credentials.username)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account is temporarily locked. Try again in {secs} seconds.",
            )

        expected_user = settings.super_admin_username or "superadmin"
        username_match = credentials.username.strip().casefold() == expected_user.casefold()

        password_valid = False
        if settings.super_admin_password_hash:
            password_valid = verify_password(credentials.password, settings.super_admin_password_hash)
        elif settings.super_admin_password:
            password_valid = credentials.password == settings.super_admin_password

        if username_match and password_valid:
            clear_failed_login(credentials.username)
            token = create_session(
                username=expected_user,
                role="SUPER_ADMIN",
                tenant_id="platform",
                expires_hours=settings.crm_token_expire_hours,
            )
            response.set_cookie(
                key="admin_session",
                value=token,
                httponly=True,
                samesite="lax",
                max_age=settings.crm_token_expire_hours * 3600,
            )
            return SuperAdminLoginResponse(
                token=token,
                username=expected_user,
                role="SUPER_ADMIN",
                tenant_id="platform",
            )

        is_now_locked, left = record_failed_login(credentials.username)
        if is_now_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Account locked for 15 minutes.",
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid platform credentials. {left} attempts remaining.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # -----------------------------------------------------------------------
    # DASHBOARD
    # -----------------------------------------------------------------------
    @router.get("/dashboard/stats")
    async def get_dashboard_stats(
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Aggregate platform metrics without clinical patient data exposure."""
        return service.get_dashboard_stats()

    # -----------------------------------------------------------------------
    # TENANT MANAGEMENT
    # -----------------------------------------------------------------------
    @router.get("/tenants")
    async def list_tenants(
        status_filter: Optional[str] = Query(None, alias="status"),
        current_admin: dict = Depends(require_super_admin),
    ) -> List[Dict[str, Any]]:
        """List all registered clinic tenants."""
        return service.list_tenants(status_filter=status_filter)

    @router.post("/tenants", status_code=status.HTTP_201_CREATED)
    async def create_tenant(
        payload: TenantCreateRequest,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Register a new clinic facility tenant."""
        try:
            return service.create_tenant(payload.model_dump(), admin_user=current_admin["username"])
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    @router.get("/tenants/{tenant_id}")
    async def get_tenant(
        tenant_id: str,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Retrieve tenant configuration details."""
        tenant = service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found.",
            )
        return tenant

    @router.patch("/tenants/{tenant_id}")
    async def update_tenant(
        tenant_id: str,
        payload: TenantUpdateRequest,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Update clinic tenant configuration."""
        try:
            return service.update_tenant(tenant_id, payload.model_dump(exclude_unset=True), admin_user=current_admin["username"])
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @router.post("/tenants/{tenant_id}/activate")
    async def activate_tenant(
        tenant_id: str,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Activate clinic tenant and restore tenant access."""
        try:
            return service.activate_tenant(tenant_id, admin_user=current_admin["username"])
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @router.post("/tenants/{tenant_id}/deactivate")
    async def deactivate_tenant(
        tenant_id: str,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Deactivate clinic tenant."""
        try:
            return service.deactivate_tenant(tenant_id, admin_user=current_admin["username"])
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @router.post("/tenants/{tenant_id}/suspend")
    async def suspend_tenant(
        tenant_id: str,
        payload: TenantSuspendRequest = TenantSuspendRequest(),
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Suspend clinic tenant."""
        try:
            return service.suspend_tenant(tenant_id, reason=payload.reason or "", admin_user=current_admin["username"])
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    # -----------------------------------------------------------------------
    # TENANT ADMIN PROVISIONING
    # -----------------------------------------------------------------------
    @router.post("/tenants/{tenant_id}/admins", status_code=status.HTTP_201_CREATED)
    async def create_tenant_admin(
        tenant_id: str,
        payload: TenantAdminCreateRequest,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Create the initial TENANT_ADMIN for a clinic."""
        try:
            return service.create_tenant_admin(
                tenant_id=tenant_id,
                username=payload.username,
                password=payload.password,
                full_name=payload.full_name or "",
                email=payload.email or "",
                admin_user=current_admin["username"],
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    # -----------------------------------------------------------------------
    # TENANT FEATURE FLAGS & SUBSCRIPTION MANAGEMENT
    # -----------------------------------------------------------------------
    @router.get("/tenants/{tenant_id}/features")
    async def get_tenant_features(
        tenant_id: str,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Retrieve effective feature toggles and subscription plan for a tenant."""
        tenant = service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant '{tenant_id}' not found.")
        flags = service.get_tenant_feature_flags(tenant_id)
        return {
            "tenant_id": tenant_id,
            "subscription_plan": tenant.get("subscription_plan", "STARTER"),
            "subscription_status": tenant.get("subscription_status", "ACTIVE"),
            "feature_flags": flags,
        }

    @router.patch("/tenants/{tenant_id}/features")
    async def update_tenant_features(
        tenant_id: str,
        payload: TenantFeaturesUpdateRequest,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Update granular feature flag toggles for a tenant."""
        try:
            return service.update_tenant_feature_flags(
                tenant_id,
                payload.feature_flags,
                admin_user=current_admin["username"],
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @router.patch("/tenants/{tenant_id}/subscription")
    async def update_tenant_subscription(
        tenant_id: str,
        payload: TenantSubscriptionUpdateRequest,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Update subscription plan and status for a tenant."""
        try:
            return service.update_tenant_subscription(
                tenant_id,
                plan=payload.subscription_plan,
                status=payload.subscription_status or "ACTIVE",
                expires_at=payload.subscription_expires_at,
                admin_user=current_admin["username"],
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    # -----------------------------------------------------------------------
    # TENANT RAG KNOWLEDGE BASE DOCUMENTS
    # -----------------------------------------------------------------------
    @router.get("/tenants/{tenant_id}/documents")
    async def list_tenant_documents(
        tenant_id: str,
        current_admin: dict = Depends(require_super_admin),
    ) -> List[Dict[str, Any]]:
        """List all indexed knowledge documents for a tenant."""
        try:
            return service.list_tenant_documents(tenant_id)
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

    @router.post("/tenants/{tenant_id}/documents", status_code=status.HTTP_201_CREATED)
    async def upload_tenant_document(
        tenant_id: str,
        file: UploadFile = File(...),
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Upload and index a PDF, TXT, or MD document into tenant's isolated knowledge base."""
        try:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
            return service.upload_tenant_document(
                tenant_id=tenant_id,
                filename=file.filename or "uploaded_doc.pdf",
                content=content,
                admin_user=current_admin["username"],
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
        except RuntimeError as err:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))

    @router.delete("/tenants/{tenant_id}/documents/{filename}")
    async def delete_tenant_document(
        tenant_id: str,
        filename: str,
        current_admin: dict = Depends(require_super_admin),
    ) -> Dict[str, Any]:
        """Delete a document from a tenant's knowledge base and re-index."""
        try:
            return service.delete_tenant_document(
                tenant_id=tenant_id,
                filename=filename,
                admin_user=current_admin["username"],
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except RuntimeError as err:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))

    # -----------------------------------------------------------------------
    # PLATFORM AUDIT
    # -----------------------------------------------------------------------

    @router.get("/audit-logs")
    async def get_audit_logs(
        limit: int = Query(50, ge=1, le=200),
        current_admin: dict = Depends(require_super_admin),
    ) -> List[Dict[str, Any]]:
        """Retrieve sanitized platform audit logs."""
        return service.get_platform_audit_logs(limit=limit)

    return router
