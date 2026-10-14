from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..rag.service import RagService
import logging


logger = logging.getLogger(__name__)


def search_clinic_knowledge(service: RagService, question: str) -> list[str]:
    try:
        from ..core.tenant import get_current_tenant
        tenant = get_current_tenant()
        if tenant and tenant.tenant_id and tenant.tenant_id not in ("default", "platform"):
            try:
                from ..rag.tenant_service import TenantRagRegistry
                registry = TenantRagRegistry()
                tenant_rag = registry.get_service(tenant.tenant_id)
                if tenant_rag.is_available():
                    return tenant_rag.search(question)
            except Exception:
                logger.warning("Tenant-specific RAG lookup failed for %s, falling back", tenant.tenant_id)
        return service.search(question)
    except Exception:
        logger.exception("RAG retrieval failed")
        return []