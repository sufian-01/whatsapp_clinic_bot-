"""Embedding boundary reserved for the production vector store."""


STOP_WORDS = {"a", "an", "and", "are", "is", "of", "the", "to", "what", "when", "where"}


def embed(text: str) -> set[str]:
    return {
        word.lower().strip(".,!?;:")
        for word in text.split()
        if word.strip() and word.lower().strip(".,!?;:") not in STOP_WORDS
    }