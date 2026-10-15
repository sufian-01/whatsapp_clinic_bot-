"""Clinic knowledge retrieval service."""

import logging
from pathlib import Path

from .loader import load_documents
from .splitter import split_documents
from .vectorstore import LocalVectorStore, get_faiss_load_error, is_faiss_available

logger = logging.getLogger(__name__)


class RagService:
    def __init__(self, knowledge_dir: Path, vectorstore_dir: Path | None = None) -> None:
        self._knowledge_dir = knowledge_dir
        self._vectorstore_dir = vectorstore_dir
        self._documents: list[str] | None = None
        self._store: LocalVectorStore | None = None
        self._initialized: bool = False

    def is_available(self) -> bool:
        """Check whether FAISS vector indexing is available on the current platform."""
        return is_faiss_available()

    def _ensure_initialized(self) -> None:
        """Lazily load documents and build or load the vector store on first use."""
        if self._initialized:
            return
        self._initialized = True

        if not self.is_available():
            err = get_faiss_load_error()
            logger.warning(
                "RAG service running in degraded mode: FAISS vector database is unavailable (%s: %s).",
                type(err).__name__ if err else "Unavailable",
                err,
            )
            self._documents = []
            self._store = LocalVectorStore.from_chunks([])
            return

        try:
            self._documents = load_documents(self._knowledge_dir)
            self._store = (
                LocalVectorStore.load(self._vectorstore_dir)
                if self._vectorstore_dir
                else LocalVectorStore.from_chunks([])
            )
            if not self._store.chunks and self._documents:
                self._store = LocalVectorStore.from_chunks(split_documents(self._documents))
                if self._vectorstore_dir:
                    self._store.save(self._vectorstore_dir)
        except Exception as exc:
            logger.warning("Failed to initialize RAG vector store: %s", exc)
            self._documents = []
            self._store = LocalVectorStore.from_chunks([])

    @property
    def store(self) -> LocalVectorStore:
        self._ensure_initialized()
        assert self._store is not None
        return self._store

    @property
    def documents(self) -> list[str]:
        self._ensure_initialized()
        assert self._documents is not None
        return self._documents

    def search(self, question: str) -> list[str]:
        self._ensure_initialized()
        if not self._store:
            return []
        return self._store.search(question)

    def ingest_pdf(self, path: Path) -> int:
        if not self.is_available():
            err = get_faiss_load_error()
            raise RuntimeError(
                f"FAISS vector database is unavailable on this system: {err}"
            )
        if not self._vectorstore_dir:
            raise RuntimeError("A persistent vector-store directory is required for PDF ingestion")

        self._ensure_initialized()
        from .pdf import extract_pdf_text

        text = extract_pdf_text(path)
        if not text:
            raise ValueError("PDF does not contain extractable text")
        if self._documents is None:
            self._documents = []
        self._documents.append(text)
        self._store = LocalVectorStore.from_chunks(split_documents(self._documents))
        self._store.save(self._vectorstore_dir)
        return len(self._store.chunks)

    def rebuild_index(self) -> int:
        """Re-scan knowledge directory (txt, md, pdf), split documents, and refresh vectorstore."""
        if not self._knowledge_dir.exists():
            self._documents = []
            self._store = LocalVectorStore.from_chunks([])
            return 0

        documents: list[str] = []
        for path in sorted(self._knowledge_dir.rglob("*")):
            if path.is_file():
                if path.suffix.lower() in {".txt", ".md"}:
                    try:
                        documents.append(path.read_text(encoding="utf-8"))
                    except Exception as exc:
                        logger.warning("Failed to read text document %s: %s", path, exc)
                elif path.suffix.lower() == ".pdf":
                    from .pdf import extract_pdf_text
                    try:
                        pdf_text = extract_pdf_text(path)
                        if pdf_text:
                            documents.append(pdf_text)
                    except Exception as exc:
                        logger.warning("Failed to extract PDF %s: %s", path, exc)

        self._documents = documents
        if self.is_available():
            chunks = split_documents(documents) if documents else []
            self._store = LocalVectorStore.from_chunks(chunks)
            if self._vectorstore_dir:
                self._store.save(self._vectorstore_dir)
            return len(chunks)
        else:
            self._store = LocalVectorStore.from_chunks([])
            return len(documents)