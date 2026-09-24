"""Clinic knowledge retrieval service."""

from pathlib import Path

from .loader import load_documents
from .splitter import split_documents
from .vectorstore import LocalVectorStore


class RagService:
    def __init__(self, knowledge_dir: Path, vectorstore_dir: Path | None = None) -> None:
        self._knowledge_dir = knowledge_dir
        self._vectorstore_dir = vectorstore_dir
        self._documents = load_documents(knowledge_dir)
        self._store = LocalVectorStore.load(vectorstore_dir) if vectorstore_dir else LocalVectorStore.from_chunks([])
        if not self._store.chunks and self._documents:
            self._store = LocalVectorStore.from_chunks(split_documents(self._documents))
            if self._vectorstore_dir:
                self._store.save(self._vectorstore_dir)

    def search(self, question: str) -> list[str]:
        return self._store.search(question)

    def ingest_pdf(self, path: Path) -> int:
        if not self._vectorstore_dir:
            raise RuntimeError("A persistent vector-store directory is required for PDF ingestion")
        from .pdf import extract_pdf_text

        text = extract_pdf_text(path)
        if not text:
            raise ValueError("PDF does not contain extractable text")
        self._documents.append(text)
        self._store = LocalVectorStore.from_chunks(split_documents(self._documents))
        self._store.save(self._vectorstore_dir)
        return len(self._store.chunks)