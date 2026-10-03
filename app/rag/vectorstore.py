"""Local retrieval store used until a hosted vector database is selected."""

from dataclasses import dataclass
import logging
from pathlib import Path
import pickle
import re
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_faiss: Any = None
_faiss_load_error: Exception | None = None
_faiss_attempted: bool = False


def get_faiss() -> Any:
    """Lazily import and return the faiss module, or None if unavailable."""
    global _faiss, _faiss_load_error, _faiss_attempted
    if not _faiss_attempted:
        _faiss_attempted = True
        try:
            import faiss
            _faiss = faiss
            _faiss_load_error = None
        except Exception as e:
            _faiss = None
            _faiss_load_error = e
            logger.warning(
                "FAISS native library could not be loaded (%s: %s). "
                "Vector retrieval and RAG knowledge indexing will be disabled.",
                type(e).__name__,
                e,
            )
    return _faiss


def is_faiss_available() -> bool:
    """Check if the faiss module is available without raising."""
    return get_faiss() is not None


def get_faiss_load_error() -> Exception | None:
    """Return the error encountered when attempting to import faiss, if any."""
    get_faiss()
    return _faiss_load_error


def reset_faiss_state() -> None:
    """Reset the lazy-loaded FAISS state (used for testing failure/success paths)."""
    global _faiss, _faiss_load_error, _faiss_attempted
    _faiss = None
    _faiss_load_error = None
    _faiss_attempted = False

try:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
except (ImportError, Exception):  # Fallback if scikit-learn DLLs are blocked by OS Application Control
    _FALLBACK_STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
        "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
        "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
        "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
        "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
        "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
        "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
        "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
        "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
        "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
        "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
        "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
        "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
        "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
        "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
    }
    ENGLISH_STOP_WORDS = frozenset(_FALLBACK_STOP_WORDS)

    class _ArrayWrapper:
        def __init__(self, arr: np.ndarray):
            self._arr = arr
        def toarray(self) -> np.ndarray:
            return self._arr

    class TfidfVectorizer:  # type: ignore[no-redef]
        def __init__(self, preprocessor=None, stop_words=None):
            self.preprocessor = preprocessor or (lambda x: x)
            self.stop_words = set(stop_words or [])
            self.vocabulary_: dict[str, int] = {}
            self.idf_: dict[str, float] = {}

        def _tokenize(self, doc: str) -> list[str]:
            text = self.preprocessor(doc)
            tokens = re.findall(r"[a-z0-9]+", text.lower())
            return [t for t in tokens if t not in self.stop_words]

        def fit_transform(self, raw_documents: list[str]) -> _ArrayWrapper:
            import math
            from collections import Counter
            docs = [self._tokenize(d) for d in raw_documents]
            n_docs = len(docs)
            vocab: dict[str, int] = {}
            df: dict[str, int] = {}
            for d in docs:
                for w in set(d):
                    df[w] = df.get(w, 0) + 1
                    if w not in vocab:
                        vocab[w] = len(vocab)
            self.vocabulary_ = vocab
            self.idf_ = {w: math.log((1 + n_docs) / (1 + df[w])) + 1.0 for w in vocab}
            return self._transform_tokens(docs)

        def transform(self, raw_documents: list[str]) -> _ArrayWrapper:
            docs = [self._tokenize(d) for d in raw_documents]
            return self._transform_tokens(docs)

        def _transform_tokens(self, docs: list[list[str]]) -> _ArrayWrapper:
            from collections import Counter
            dim = max(1, len(self.vocabulary_))
            matrix = np.zeros((len(docs), dim), dtype=np.float32)
            for i, doc in enumerate(docs):
                if not doc:
                    continue
                counts = Counter(doc)
                total = len(doc)
                for w, count in counts.items():
                    if w in self.vocabulary_:
                        matrix[i, self.vocabulary_[w]] = (count / total) * self.idf_[w]
                norm = np.linalg.norm(matrix[i])
                if norm > 0:
                    matrix[i] /= norm
            return _ArrayWrapper(matrix)


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
    vectorizer: Any | None = None
    index: Any | None = None

    @classmethod
    def from_chunks(cls, chunks: list[str]) -> "LocalVectorStore":
        store = cls(chunks)
        if chunks:
            faiss_module = get_faiss()
            if faiss_module is None:
                err = get_faiss_load_error()
                raise RuntimeError(
                    f"Cannot build vector index because FAISS is unavailable: {err}"
                )
            store.vectorizer = TfidfVectorizer(
                preprocessor=normalize_text,
                stop_words=list(ENGLISH_STOP_WORDS | STOP_WORDS),
            )
            vectors = store.vectorizer.fit_transform(chunks).toarray().astype("float32")
            store.index = faiss_module.IndexFlatIP(vectors.shape[1])
            store.index.add(vectors)
        return store

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "metadata.pkl").open("wb") as file:
            pickle.dump((self.chunks, self.vectorizer), file)
        if self.index is not None:
            faiss_module = get_faiss()
            if faiss_module is not None:
                faiss_module.write_index(self.index, str(directory / "index.faiss"))

    @classmethod
    def load(cls, directory: Path) -> "LocalVectorStore":
        metadata = directory / "metadata.pkl"
        index_path = directory / "index.faiss"
        if not metadata.exists() or not index_path.exists():
            return cls.from_chunks([])
        faiss_module = get_faiss()
        if faiss_module is None:
            logger.warning(
                "Skipping FAISS vector store loading from %s because FAISS is unavailable.",
                directory,
            )
            return cls.from_chunks([])
        try:
            with metadata.open("rb") as file:
                chunks, vectorizer = pickle.load(file)
            store = cls(chunks, vectorizer, faiss_module.read_index(str(index_path)))
            return store
        except Exception as exc:
            logger.warning("Failed to load vector store from %s: %s", directory, exc)
            return cls.from_chunks([])

    def search(self, query: str, limit: int = 3) -> list[str]:
        if not self.index or not self.vectorizer or not self.chunks:
            return []
        vector = self.vectorizer.transform([query]).toarray().astype("float32")
        scores, positions = self.index.search(vector, min(limit, len(self.chunks)))
        return [self.chunks[position] for score, position in zip(scores[0], positions[0]) if score > 0 and position >= 0]