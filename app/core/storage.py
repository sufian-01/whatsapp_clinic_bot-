"""Tenant-Isolated File and Storage Management.

Enforces structural partitioning of file storage paths by tenant_id,
preventing cross-tenant directory traversal or file access.
"""

from pathlib import Path
import re
from typing import Optional

from .config import ROOT_DIR


ALLOWED_STORAGE_CATEGORIES = frozenset({
    "knowledge",
    "doctors",
    "prescriptions",
    "invoices",
    "documents",
    "uploads",
})


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError(f"Invalid or unsafe filename: '{filename}'")
    cleaned = Path(filename).name.strip()
    # Remove any dangerous characters
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', cleaned)
    if not cleaned or cleaned in (".", ".."):
        raise ValueError(f"Invalid or unsafe filename: '{filename}'")
    return cleaned


def get_tenant_storage_root(tenant_id: str, base_dir: Optional[Path] = None) -> Path:
    """Return the root storage directory for a specific tenant."""
    clean_tenant = str(tenant_id).strip()
    if not clean_tenant or clean_tenant in (".", ".."):
        raise ValueError(f"Invalid tenant_id for storage: '{tenant_id}'")

    root = base_dir or (ROOT_DIR / "data")
    return (root / "tenants" / clean_tenant).resolve()


def get_tenant_storage_path(
    tenant_id: str,
    category: str,
    filename: str = "",
    base_dir: Optional[Path] = None,
    create_dirs: bool = False,
) -> Path:
    """Return a validated, tenant-partitioned filesystem path.

    Example:
        get_tenant_storage_path("clinic_1", "prescriptions", "RX-123.pdf")
        -> ".../data/tenants/clinic_1/prescriptions/RX-123.pdf"
    """
    clean_category = category.strip().casefold()
    if clean_category not in ALLOWED_STORAGE_CATEGORIES:
        raise ValueError(
            f"Invalid storage category '{category}'. Allowed: {sorted(ALLOWED_STORAGE_CATEGORIES)}"
        )

    tenant_root = get_tenant_storage_root(tenant_id, base_dir)
    target_dir = tenant_root / clean_category

    if create_dirs:
        target_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        clean_name = sanitize_filename(filename)
        target_path = (target_dir / clean_name).resolve()
    else:
        target_path = target_dir.resolve()

    # Path traversal validation: target_path must strictly reside within tenant_root
    if not str(target_path).startswith(str(tenant_root)):
        raise PermissionError(f"Path traversal detected: '{target_path}' is outside tenant root '{tenant_root}'")

    return target_path


def validate_tenant_file_access(tenant_id: str, file_path: Path, base_dir: Optional[Path] = None) -> bool:
    """Verify whether a file path belongs strictly to the given tenant."""
    try:
        tenant_root = str(get_tenant_storage_root(tenant_id, base_dir))
        resolved_file = str(file_path.resolve())
        return resolved_file.startswith(tenant_root)
    except Exception:
        return False
