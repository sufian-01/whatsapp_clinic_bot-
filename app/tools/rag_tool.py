from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..rag.service import RagService
import logging


logger = logging.getLogger(__name__)


def search_clinic_knowledge(
    service: RagService,
    question: str,
    tenant_id: Optional[str] = None,
) -> list[str]:
    try:
        from ..core.tenant import get_current_tenant
        if not tenant_id:
            curr = get_current_tenant()
            if curr and curr.tenant_id:
                tenant_id = curr.tenant_id

        target_tid = str(tenant_id or "").strip()
        if target_tid and target_tid != "platform":
            try:
                from ..rag.tenant_service import get_tenant_rag_registry
                registry = get_tenant_rag_registry()
                tenant_rag = registry.get_service(target_tid)
                if tenant_rag.is_available():
                    results = tenant_rag.search(question)
                    if results:
                        return results
            except Exception as exc:
                logger.warning("Tenant-specific RAG lookup failed for %s, falling back: %s", target_tid, exc, exc_info=True)
        return service.search(question) if service else []
    except Exception:
        logger.exception("RAG retrieval failed")
        return []