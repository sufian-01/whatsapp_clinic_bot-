"""Load clinic knowledge documents from disk."""

from pathlib import Path


def load_documents(directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    documents: list[str] = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
            documents.append(path.read_text(encoding="utf-8"))
    return documents