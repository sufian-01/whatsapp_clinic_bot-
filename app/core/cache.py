"""Tenant-Isolated Caching Utilities.

Ensures that cached items are strictly partitioned by tenant identity,
preventing cross-tenant cache pollution or data leakage.
"""

from collections import defaultdict
import hashlib
import json
from threading import RLock
import time
from typing import Any, Dict, Optional, Tuple


def build_tenant_cache_key(tenant_id: str, resource: str, *args: Any, **kwargs: Any) -> str:
    """Build a deterministic, tenant-isolated cache key.

    Example:
        build_tenant_cache_key("tenant_123", "doctors", "cardiology")
        -> "tenant:tenant_123:doctors:cardiology"
    """
    clean_tenant = str(tenant_id).strip()
    if not clean_tenant:
        raise ValueError("Tenant-isolated cache key requires a non-empty tenant_id.")

    clean_resource = str(resource).strip().casefold()
    parts = [f"tenant:{clean_tenant}", clean_resource]

    if args:
        parts.extend(str(a).strip().casefold() for a in args)

    if kwargs:
        sorted_kw = sorted((k.casefold(), str(v).strip().casefold()) for k, v in kwargs.items())
        parts.extend(f"{k}={v}" for k, v in sorted_kw)

    return ":".join(parts)


class TenantCache:
    """Thread-safe in-memory cache with automatic tenant partition and invalidation."""

    def __init__(self, default_ttl: float = 60.0) -> None:
        self.default_ttl = default_ttl
        self._lock = RLock()
        # key -> (value, expiry_timestamp, tenant_id, resource)
        self._store: Dict[str, Tuple[Any, float, str, str]] = {}

    def get(self, tenant_id: str, resource: str, *args: Any, **kwargs: Any) -> Optional[Any]:
        """Retrieve a cached value for a specific tenant and resource."""
        key = build_tenant_cache_key(tenant_id, resource, *args, **kwargs)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expiry, stored_tenant, _ = entry
            if time.monotonic() > expiry:
                del self._store[key]
                return None
            # Double check tenant identity
            if stored_tenant != str(tenant_id).strip():
                return None
            return value

    def set(
        self,
        tenant_id: str,
        resource: str,
        value: Any,
        *args: Any,
        ttl: Optional[float] = None,
        **kwargs: Any,
    ) -> str:
        """Store a cached value strictly bound to a tenant."""
        key = build_tenant_cache_key(tenant_id, resource, *args, **kwargs)
        clean_ttl = ttl if ttl is not None else self.default_ttl
        expiry = time.monotonic() + clean_ttl
        with self._lock:
            self._store[key] = (value, expiry, str(tenant_id).strip(), str(resource).strip().casefold())
        return key

    def invalidate_tenant(self, tenant_id: str) -> int:
        """Purge all cached items belonging to a specific tenant."""
        clean_tenant = str(tenant_id).strip()
        count = 0
        with self._lock:
            keys_to_delete = [
                k for k, (_, _, t_id, _) in self._store.items()
                if t_id == clean_tenant
            ]
            for k in keys_to_delete:
                del self._store[k]
                count += 1
        return count

    def invalidate_resource(self, tenant_id: str, resource: str) -> int:
        """Purge all cached items for a specific resource under a tenant."""
        clean_tenant = str(tenant_id).strip()
        clean_resource = str(resource).strip().casefold()
        count = 0
        with self._lock:
            keys_to_delete = [
                k for k, (_, _, t_id, r_name) in self._store.items()
                if t_id == clean_tenant and r_name == clean_resource
            ]
            for k in keys_to_delete:
                del self._store[k]
                count += 1
        return count

    def clear(self) -> None:
        """Clear the entire cache across all tenants."""
        with self._lock:
            self._store.clear()

