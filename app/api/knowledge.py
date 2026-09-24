"""Clinic knowledge upload endpoint."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..rag.service import RagService


def create_knowledge_router(knowledge_dir: Path, rag: RagService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

    @router.post("/upload")
    async def upload_pdf(file: UploadFile = File(...)) -> dict[str, int | str]:
        if file.content_type != "application/pdf" or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=415, detail="Only PDF files are accepted")
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        destination = knowledge_dir / f"{uuid4().hex}.pdf"
        try:
            destination.write_bytes(await file.read())
            chunks = rag.ingest_pdf(destination)
        except ValueError as error:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception:
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail="The PDF could not be indexed") from None
        return {"status": "indexed", "filename": destination.name, "chunks": chunks}

    return router