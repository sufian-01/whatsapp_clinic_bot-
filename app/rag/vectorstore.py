"""Local retrieval store used until a hosted vector database is selected."""

from dataclasses import dataclass
import pickle
from pathlib import Path
import re

import faiss
import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer


STOP_WORDS = {
    "price",
    "cost",
    "available",
    "availability",
    "information",
}


def normalize_text(text: str) -> str:
    replacements = {
        "tests": "test",
        "doctors": "doctor",
        "timings": "timing",
        "services": "service",
        "availability": "available",
    }
    words = re.findall(r"[a-z0-9]+", text.lower())
    return " ".join(replacements.get(word, word) for word in words)


@dataclass
class LocalVectorStore:
    chunks: list[str]
    vectorizer: TfidfVectorizer | None = None
    index: faiss.Index | None = None

    @classmethod
    def from_chunks(cls, chunks: list[str]) -> "LocalVectorStore":
        store = cls(chunks)
        if chunks:
            store.vectorizer = TfidfVectorizer(
                preprocessor=normalize_text,
                stop_words=list(ENGLISH_STOP_WORDS | STOP_WORDS),
            )
            vectors = store.vectorizer.fit_transform(chunks).toarray().astype("float32")
            store.index = faiss.IndexFlatIP(vectors.shape[1])
            store.index.add(vectors)
        return store

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "metadata.pkl").open("wb") as file:
            pickle.dump((self.chunks, self.vectorizer), file)
        if self.index is not None:
            faiss.write_index(self.index, str(directory / "index.faiss"))

    @classmethod
    def load(cls, directory: Path) -> "LocalVectorStore":
        metadata = directory / "metadata.pkl"
        index_path = directory / "index.faiss"
        if not metadata.exists() or not index_path.exists():
            return cls.from_chunks([])
        with metadata.open("rb") as file:
            chunks, vectorizer = pickle.load(file)
        store = cls(chunks, vectorizer, faiss.read_index(str(index_path)))
        return store

    def search(self, query: str, limit: int = 3) -> list[str]:
        if not self.index or not self.vectorizer or not self.chunks:
            return []
        vector = self.vectorizer.transform([query]).toarray().astype("float32")
        scores, positions = self.index.search(vector, min(limit, len(self.chunks)))
        return [self.chunks[position] for score, position in zip(scores[0], positions[0]) if score > 0 and position >= 0]