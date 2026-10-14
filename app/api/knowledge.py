"""Clinic knowledge upload endpoint."""

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..core.auth import get_current_admin
from ..rag.service import RagService

logger = logging.getLogger(__name__)


def create_knowledge_router(knowledge_dir: Path, rag: RagService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

    @router.get("/status")
    async def get_knowledge_status() -> dict[str, Any]:
        """Check availability of the RAG knowledge retrieval and indexing service."""
        available = rag.is_available()
        return {
            "status": "available" if available else "unavailable",
            "faiss_available": available,
            "detail": (
                "RAG knowledge retrieval service is operational."
                if available
                else "RAG knowledge retrieval service is unavailable: FAISS vector database could not be loaded on this system."
            ),
        }

    @router.post("/upload")
    async def upload_pdf(
        file: UploadFile = File(...),
        current_admin: dict = Depends(get_current_admin),
    ) -> dict[str, int | str]:
        from ..core.rbac import Permission, has_permission
        if not has_permission(current_admin.get("role", ""), Permission.KNOWLEDGE_UPLOAD):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Knowledge upload requires TENANT_ADMIN or SUPER_ADMIN permissions.",
            )

        if not rag.is_available():
            logger.warning(
                "PDF upload rejected on /api/v1/knowledge/upload because FAISS is unavailable."
            )
            raise HTTPException(
                status_code=503,
                detail="RAG knowledge service is unavailable: FAISS vector database is not available on this system.",
            )

        if file.content_type != "application/pdf" or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=415, detail="Only PDF files are accepted")

        tenant_id = current_admin.get("tenant_id") or "default"
        if tenant_id and tenant_id != "default":
            from ..core.storage import get_tenant_storage_path
            try:
                destination = get_tenant_storage_path(tenant_id, "knowledge", f"{uuid4().hex}.pdf", create_dirs=True)
            except Exception:
                knowledge_dir.mkdir(parents=True, exist_ok=True)
                destination = knowledge_dir / f"{uuid4().hex}.pdf"
        else:
            knowledge_dir.mkdir(parents=True, exist_ok=True)
            destination = knowledge_dir / f"{uuid4().hex}.pdf"
        try:
            destination.write_bytes(await file.read())
            chunks = rag.ingest_pdf(destination)
        except RuntimeError as error:
            destination.unlink(missing_ok=True)
            if not rag.is_available():
                logger.warning("RAG indexing failed due to unavailable FAISS: %s", error)
                raise HTTPException(
                    status_code=503,
                    detail=f"RAG knowledge service is unavailable: {error}",
                ) from error
            logger.error("RAG ingestion runtime error: %s", error)
            raise HTTPException(status_code=500, detail=str(error)) from error
        except ValueError as error:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            destination.unlink(missing_ok=True)
            if not rag.is_available():
                logger.warning("RAG indexing failed due to unavailable FAISS: %s", error)
                raise HTTPException(
                    status_code=503,
                    detail="RAG knowledge service is unavailable: FAISS native library is not loaded.",
                ) from error
            logger.exception("Unexpected error during PDF ingestion: %s", error)
            raise HTTPException(status_code=500, detail="The PDF could not be indexed") from None

        return {"status": "indexed", "filename": destination.name, "chunks": chunks}

    return router