"""Tenant Management and Super Admin Service.

Provides platform-level management for multi-tenant clinics:
- Tenant/clinic registration, configuration, and lifecycle (Active, Inactive, Suspended)
- Initial Tenant Admin user provisioning
- Platform dashboard aggregated statistics
- Platform-level audit logging with secret redaction
- Least-privilege separation between platform administration and patient clinical data
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import secrets
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.auth import hash_password
from ..core.tenant import get_tenant_status, set_tenant_status
from .audit_service import AuditService

logger = logging.getLogger(__name__)


class TenantManagementService:
    """Thread-safe platform administration and tenant lifecycle service."""

    def __init__(
        self,
        audit_service: Optional[AuditService] = None,
        session_factory=None,
    ) -> None:
        self.audit = audit_service or AuditService()
        self.session_factory = session_factory
        self._lock = RLock()

        # In-memory tenant and admin store for fast lookup and standalone operation
        self._tenants: Dict[str, Dict[str, Any]] = {}
        self._tenant_admins: Dict[str, Dict[str, Any]] = {}  # username -> admin dict
        self._platform_audit_events: List[Dict[str, Any]] = []

        # Seed default clinic tenant
        self._seed_default_tenant()
        if self.session_factory:
            self._load_from_database()

    def _seed_default_tenant(self) -> None:
        """Seed the baseline default tenant."""
        default_id = "default"
        self._tenants[default_id] = {
            "id": default_id,
            "name": "XYZ Clinic",
            "legal_name": "XYZ Healthcare Pvt Ltd",
            "logo": "",
            "phone": "6200126662",
            "email": "info@xyzclinic.com",
            "website": "https://xyzclinic.com",
            "address": "Main Road, Medical District",
            "timezone": "Asia/Kolkata",
            "currency": "INR",
            "working_days": "Monday - Saturday",
            "working_hours": "09:00 - 18:00",
            "appointment_duration": 30,
            "booking_settings": "{}",
            "rag_config_status": "CONFIGURED",
            "channel_config_status": "CONFIGURED",
            "status": "ACTIVE",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        set_tenant_status(default_id, "ACTIVE")

    def _load_from_database(self) -> None:
        """Load tenant facilities and tenant admins from the PostgreSQL database."""
        if not self.session_factory:
            return
        try:
            from sqlalchemy import select
            from ..db.models import Clinic, User
            with self.session_factory() as session:
                clinics = session.execute(select(Clinic)).scalars().all()
                with self._lock:
                    for c in clinics:
                        st = (c.status or "ACTIVE").upper()
                        self._tenants[c.id] = {
                            "id": c.id,
                            "name": c.name,
                            "legal_name": c.legal_name or c.name,
                            "logo": c.logo or "",
                            "phone": c.phone or "",
                            "email": c.email or "",
                            "website": c.website or "",
                            "address": c.address or "",
                            "timezone": c.timezone or "Asia/Kolkata",
                            "currency": c.currency or "INR",
                            "working_days": c.working_days or "Monday - Saturday",
                            "working_hours": c.working_hours or "09:00 - 18:00",
                            "appointment_duration": c.appointment_duration or 30,
                            "booking_settings": c.booking_settings or "{}",
                            "rag_config_status": c.rag_config_status or "CONFIGURED",
                            "channel_config_status": c.channel_config_status or "CONFIGURED",
                            "status": st,
                            "is_active": c.is_active,
                            "created_at": c.created_at.isoformat() if c.created_at else datetime.now(timezone.utc).isoformat(),
                            "updated_at": c.updated_at.isoformat() if c.updated_at else datetime.now(timezone.utc).isoformat(),
                        }
                        set_tenant_status(c.id, st)

                admins = session.execute(select(User).where(User.role == "TENANT_ADMIN")).scalars().all()
                with self._lock:
                    for a in admins:
                        norm_u = a.username.casefold()
                        self._tenant_admins[norm_u] = {
                            "id": a.id,
                            "tenant_id": a.tenant_id,
                            "username": a.username,
                            "full_name": a.full_name or a.username,
                            "email": a.email or "",
                            "role": "TENANT_ADMIN",
                            "status": a.status or "Active",
                            "is_active": a.is_active,
                            "must_change_password": a.must_change_password,
                            "created_at": a.created_at.isoformat() if a.created_at else datetime.now(timezone.utc).isoformat(),
                        }
        except Exception as e:
            logger.warning("Could not load tenants from database: %s", e)

    def _record_platform_audit(
        self,
        user: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record sanitized platform audit entry."""
        sanitized = dict(details or {})
        # Redact any accidental sensitive parameters
        for sensitive_key in ("password", "password_hash", "token", "secret", "api_key"):
            if sensitive_key in sanitized:
                sanitized[sensitive_key] = "[REDACTED]"

        entry = {
            "audit_id": f"plt_{secrets.token_hex(6)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": sanitized,
        }
        with self._lock:
            self._platform_audit_events.append(entry)

        # Also emit to centralized audit service if present
        try:
            self.audit.record(
                user=user,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=sanitized,
            )
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Platform Dashboard Metrics
    # -----------------------------------------------------------------------
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Aggregate platform metrics without exposing patient clinical data."""
        with self._lock:
            total_tenants = len(self._tenants)
            active_tenants = sum(1 for t in self._tenants.values() if t.get("status") == "ACTIVE")
            inactive_tenants = sum(1 for t in self._tenants.values() if t.get("status") == "INACTIVE")
            suspended_tenants = sum(1 for t in self._tenants.values() if t.get("status") == "SUSPENDED")
            total_admins = len(self._tenant_admins)
            ready_rag = sum(1 for t in self._tenants.values() if t.get("rag_config_status") == "CONFIGURED")

        return {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "inactive_tenants": inactive_tenants,
            "suspended_tenants": suspended_tenants,
            "total_tenant_admins": total_admins,
            "system_health": "HEALTHY",
            "rag_status_summary": {
                "configured": ready_rag,
                "pending": total_tenants - ready_rag,
            },
            "channel_config_summary": {
                "telegram_active": True,
                "whatsapp_ready": False,
            },
        }

    # -----------------------------------------------------------------------
    # Tenant Operations
    # -----------------------------------------------------------------------
    def list_tenants(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all clinics, with sensitive payment credentials omitted."""
        with self._lock:
            results = []
            for t in self._tenants.values():
                if status_filter and t.get("status", "").casefold() != status_filter.strip().casefold():
                    continue
                safe = dict(t)
                safe.pop("upi_id", None)
                safe["admin_count"] = sum(
                    1 for a in self._tenant_admins.values() if a.get("tenant_id") == t["id"]
                )
                results.append(safe)
        return results

    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single tenant metadata without secrets."""
        clean_id = str(tenant_id).strip()
        with self._lock:
            t = self._tenants.get(clean_id)
            if not t:
                return None
            safe = dict(t)
            safe.pop("upi_id", None)
            safe["admin_count"] = sum(
                1 for a in self._tenant_admins.values() if a.get("tenant_id") == clean_id
            )
            return safe

    def create_tenant(self, data: Dict[str, Any], admin_user: str = "superadmin") -> Dict[str, Any]:
        """Create a new clinic facility tenant."""
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("Clinic name is required.")

        custom_id = data.get("id")
        if custom_id and str(custom_id).strip():
            tenant_id = re.sub(r'[^a-zA-Z0-9_\-]', '', str(custom_id).strip()).casefold()
        else:
            slug = re.sub(r'[^a-zA-Z0-9]', '_', name.casefold())[:16].strip('_')
            tenant_id = f"cln_{slug}_{secrets.token_hex(3)}"

        with self._lock:
            if tenant_id in self._tenants:
                raise ValueError(f"Tenant with ID '{tenant_id}' already exists.")

            now = datetime.now(timezone.utc).isoformat()
            status_val = str(data.get("status", "ACTIVE")).strip().upper()
            if status_val not in ("ACTIVE", "INACTIVE", "SUSPENDED"):
                status_val = "ACTIVE"

            tenant_record = {
                "id": tenant_id,
                "name": name,
                "legal_name": data.get("legal_name") or name,
                "logo": data.get("logo") or "",
                "phone": data.get("phone") or "",
                "email": data.get("email") or "",
                "website": data.get("website") or "",
                "address": data.get("address") or "",
                "timezone": data.get("timezone") or "Asia/Kolkata",
                "currency": data.get("currency") or "INR",
                "working_days": data.get("working_days") or "Monday - Friday",
                "working_hours": data.get("working_hours") or "09:00 - 17:00",
                "appointment_duration": int(data.get("appointment_duration", 30)),
                "booking_settings": data.get("booking_settings") or "{}",
                "rag_config_status": data.get("rag_config_status") or "CONFIGURED",
                "channel_config_status": data.get("channel_config_status") or "CONFIGURED",
                "status": status_val,
                "is_active": (status_val == "ACTIVE"),
                "created_at": now,
                "updated_at": now,
            }

            self._tenants[tenant_id] = tenant_record
            set_tenant_status(tenant_id, status_val)

        if self.session_factory:
            try:
                from ..db.models import Clinic
                with self.session_factory() as session:
                    c = Clinic(
                        id=tenant_id,
                        name=name,
                        legal_name=tenant_record["legal_name"],
                        logo=tenant_record["logo"],
                        phone=tenant_record["phone"],
                        email=tenant_record["email"],
                        website=tenant_record["website"],
                        address=tenant_record["address"],
                        timezone=tenant_record["timezone"],
                        currency=tenant_record["currency"],
                        working_days=tenant_record["working_days"],
                        working_hours=tenant_record["working_hours"],
                        appointment_duration=tenant_record["appointment_duration"],
                        booking_settings=tenant_record["booking_settings"],
                        status=status_val,
                        is_active=tenant_record["is_active"],
                    )
                    session.add(c)
                    session.commit()
            except Exception as e:
                logger.error("Failed to persist clinic to database: %s", e)

        self._record_platform_audit(
            user=admin_user,
            action="TENANT_CREATE",
            entity_type="tenant",
            entity_id=tenant_id,
            details={"name": name, "status": status_val},
        )
        safe = dict(tenant_record)
        safe["admin_count"] = 0
        return safe

    def update_tenant(self, tenant_id: str, data: Dict[str, Any], admin_user: str = "superadmin") -> Dict[str, Any]:
        """Update clinic tenant metadata."""
        clean_id = str(tenant_id).strip()
        with self._lock:
            if clean_id not in self._tenants:
                raise ValueError(f"Tenant '{clean_id}' not found.")

            t = self._tenants[clean_id]
            allowed_fields = (
                "name", "legal_name", "logo", "phone", "email", "website",
                "address", "timezone", "currency", "working_days", "working_hours",
                "appointment_duration", "booking_settings", "rag_config_status",
                "channel_config_status",
            )
            changes = {}
            for k in allowed_fields:
                if k in data and data[k] is not None:
                    t[k] = data[k]
                    changes[k] = str(data[k])

            t["updated_at"] = datetime.now(timezone.utc).isoformat()
            safe = dict(t)

        if self.session_factory:
            try:
                from sqlalchemy import select
                from ..db.models import Clinic
                with self.session_factory() as session:
                    c = session.execute(select(Clinic).where(Clinic.id == clean_id)).scalar_one_or_none()
                    if c:
                        for k, v in changes.items():
                            if hasattr(c, k):
                                setattr(c, k, v)
                        session.commit()
            except Exception as e:
                logger.error("Failed to update clinic in database: %s", e)

        self._record_platform_audit(
            user=admin_user,
            action="TENANT_UPDATE",
            entity_type="tenant",
            entity_id=clean_id,
            details={"updated_fields": list(changes.keys())},
        )
        return safe

    def _sync_tenant_status_to_db(self, tenant_id: str, status_val: str, is_active: bool) -> None:
        if not self.session_factory:
            return
        try:
            from sqlalchemy import select
            from ..db.models import Clinic
            with self.session_factory() as session:
                c = session.execute(select(Clinic).where(Clinic.id == tenant_id)).scalar_one_or_none()
                if c:
                    c.status = status_val
                    c.is_active = is_active
                    session.commit()
        except Exception as e:
            logger.error("Failed to update clinic status in database: %s", e)

    def activate_tenant(self, tenant_id: str, admin_user: str = "superadmin") -> Dict[str, Any]:
        """Activate clinic tenant and restore access."""
        clean_id = str(tenant_id).strip()
        with self._lock:
            if clean_id not in self._tenants:
                raise ValueError(f"Tenant '{clean_id}' not found.")
            t = self._tenants[clean_id]
            t["status"] = "ACTIVE"
            t["is_active"] = True
            t["updated_at"] = datetime.now(timezone.utc).isoformat()
            set_tenant_status(clean_id, "ACTIVE")
            safe = dict(t)

        self._sync_tenant_status_to_db(clean_id, "ACTIVE", True)

        self._record_platform_audit(
            user=admin_user,
            action="TENANT_ACTIVATE",
            entity_type="tenant",
            entity_id=clean_id,
            details={"status": "ACTIVE"},
        )
        return safe

    def deactivate_tenant(self, tenant_id: str, admin_user: str = "superadmin") -> Dict[str, Any]:
        """Deactivate clinic tenant."""
        clean_id = str(tenant_id).strip()
        with self._lock:
            if clean_id not in self._tenants:
                raise ValueError(f"Tenant '{clean_id}' not found.")
            t = self._tenants[clean_id]
            t["status"] = "INACTIVE"
            t["is_active"] = False
            t["updated_at"] = datetime.now(timezone.utc).isoformat()
            set_tenant_status(clean_id, "INACTIVE")
            safe = dict(t)

        self._sync_tenant_status_to_db(clean_id, "INACTIVE", False)

        self._record_platform_audit(
            user=admin_user,
            action="TENANT_DEACTIVATE",
            entity_type="tenant",
            entity_id=clean_id,
            details={"status": "INACTIVE"},
        )
        return safe

    def suspend_tenant(self, tenant_id: str, reason: str = "", admin_user: str = "superadmin") -> Dict[str, Any]:
        """Suspend clinic tenant."""
        clean_id = str(tenant_id).strip()
        with self._lock:
            if clean_id not in self._tenants:
                raise ValueError(f"Tenant '{clean_id}' not found.")
            t = self._tenants[clean_id]
            t["status"] = "SUSPENDED"
            t["is_active"] = False
            t["updated_at"] = datetime.now(timezone.utc).isoformat()
            set_tenant_status(clean_id, "SUSPENDED")
            safe = dict(t)

        self._sync_tenant_status_to_db(clean_id, "SUSPENDED", False)

        self._record_platform_audit(
            user=admin_user,
            action="TENANT_SUSPEND",
            entity_type="tenant",
            entity_id=clean_id,
            details={"status": "SUSPENDED", "reason": reason.strip()},
        )
        return safe

    # -----------------------------------------------------------------------
    # Provision Initial Tenant Admin
    # -----------------------------------------------------------------------
    def create_tenant_admin(
        self,
        tenant_id: str,
        username: str,
        password: str,
        full_name: str = "",
        email: str = "",
        admin_user: str = "superadmin",
    ) -> Dict[str, Any]:
        """Create initial administrator user bound strictly to the given tenant."""
        clean_tid = str(tenant_id).strip()
        with self._lock:
            if clean_tid not in self._tenants:
                raise ValueError(f"Target tenant '{clean_tid}' does not exist.")

        norm_user = username.strip().casefold()
        if not norm_user:
            raise ValueError("Username is required.")
        if not re.match(r"^[a-zA-Z0-9_\-\.]{3,32}$", username.strip()):
            raise ValueError("Username must be 3-32 characters (alphanumeric, dots, dashes, underscores).")

        # Password validation
        if len(password) < 8 or not re.search(r"\d", password) or not re.search(r"[a-zA-Z]", password):
            raise ValueError("Password must be at least 8 characters long with letters and numbers.")

        with self._lock:
            if norm_user in self._tenant_admins:
                raise ValueError(f"User '{username.strip()}' already exists.")

            hashed_pw = hash_password(password)
            user_record = {
                "id": f"usr_{secrets.token_hex(6)}",
                "tenant_id": clean_tid,
                "username": username.strip(),
                "full_name": full_name.strip() or username.strip(),
                "email": email.strip(),
                "role": "TENANT_ADMIN",  # Strictly bounded to TENANT_ADMIN
                "password_hash": hashed_pw,
                "status": "Active",
                "is_active": True,
                "must_change_password": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._tenant_admins[norm_user] = user_record

        if self.session_factory:
            try:
                from ..db.models import User
                with self.session_factory() as session:
                    u = User(
                        tenant_id=clean_tid,
                        username=norm_user,
                        password_hash=hashed_pw,
                        role="TENANT_ADMIN",
                        full_name=user_record["full_name"],
                        email=email.strip() or None,
                        status="Active",
                        must_change_password=True,
                    )
                    session.add(u)
                    session.commit()
            except Exception as e:
                logger.error("Failed to persist tenant admin to database: %s", e)

        self._record_platform_audit(
            user=admin_user,
            action="TENANT_ADMIN_CREATE",
            entity_type="user",
            entity_id=norm_user,
            details={"tenant_id": clean_tid, "username": username.strip(), "role": "TENANT_ADMIN"},
        )

        # Never return password hash in response
        safe = dict(user_record)
        safe.pop("password_hash", None)
        return safe

    # -----------------------------------------------------------------------
    # Platform Audit Log Retrieval
    # -----------------------------------------------------------------------
    def get_platform_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent platform operations with all sensitive values redacted."""
        with self._lock:
            events = list(self._platform_audit_events)
        # Return in descending chronological order
        return sorted(events, key=lambda x: x["timestamp"], reverse=True)[:limit]
