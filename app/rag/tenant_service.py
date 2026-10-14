"""Tenant-Isolated RAG Retrieval and Ingestion Service.

Guarantees that each clinic tenant operates on its own dedicated knowledge
directory and vector store index, preventing cross-tenant document leakage.
"""

import logging
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional

from ..core.storage import get_tenant_storage_path, get_tenant_storage_root
from .service import RagService

logger = logging.getLogger(__name__)


class TenantRagService:
    """RAG service scoped strictly to a specific clinic tenant."""

    def __init__(
        self,
        tenant_id: str,
        base_dir: Optional[Path] = None,
    ) -> None:
        clean_tenant = str(tenant_id).strip()
        if not clean_tenant:
            raise ValueError("TenantRagService requires a valid, non-empty tenant_id.")

        self.tenant_id = clean_tenant
        self.knowledge_dir = get_tenant_storage_path(
            clean_tenant,
            "knowledge",
            base_dir=base_dir,
            create_dirs=True,
        )
        self.vectorstore_dir = get_tenant_storage_root(clean_tenant, base_dir=base_dir) / "vectorstore"
        self._inner = RagService(self.knowledge_dir, self.vectorstore_dir)

    def is_available(self) -> bool:
        """Check whether RAG is operational for this tenant."""
        return self._inner.is_available()

    def search(self, query: str, k: int = 4) -> List[str]:
        """Search strictly within this tenant's indexed knowledge base."""
        return self._inner.search(query, k=k)

    def get_relevant_context(self, query: str, k: int = 3) -> str:
        """Retrieve relevant context for conversational prompting."""
        return self._inner.get_relevant_context(query, k=k)

    def ingest_pdf(self, file_path: Path, filename: str) -> int:
        """Ingest a PDF document into this tenant's isolated knowledge base."""
        return self._inner.ingest_pdf(file_path, filename)


class TenantRagRegistry:
    """Thread-safe registry for tenant-scoped RAG service instances."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir
        self._services: Dict[str, TenantRagService] = {}
        self._lock = RLock()

    def get_service(self, tenant_id: str) -> TenantRagService:
        """Retrieve or initialize the isolated RAG service for a tenant."""
        clean_tenant = str(tenant_id).strip()
        with self._lock:
            if clean_tenant not in self._services:
                self._services[clean_tenant] = TenantRagService(clean_tenant, self.base_dir)
            return self._services[clean_tenant]

    def clear(self) -> None:
        """Clear cached service instances."""
        with self._lock:
            self._services.clear()

