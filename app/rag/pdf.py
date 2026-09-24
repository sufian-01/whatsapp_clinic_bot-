"""PDF extraction and indexing."""

from pathlib import Path

from pypdf import PdfReader

from .splitter import split_documents
from .vectorstore import LocalVectorStore


def extract_pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages).strip()


def index_pdf(path: Path, vectorstore_dir: Path, existing_documents: list[str]) -> LocalVectorStore:
    text = extract_pdf_text(path)
    if not text:
        raise ValueError("PDF does not contain extractable text")
    chunks = split_documents(existing_documents + [text])
    store = LocalVectorStore.from_chunks(chunks)
    store.save(vectorstore_dir)
    return store