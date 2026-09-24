"""RAG tool exposed to graph nodes."""

from ..rag.service import RagService
import logging


logger = logging.getLogger(__name__)


def search_clinic_knowledge(service: RagService, question: str) -> list[str]:
    try:
        return service.search(question)
    except Exception:
        logger.exception("RAG retrieval failed")
        return []