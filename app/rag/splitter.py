"""Small deterministic text splitter for the initial local knowledge store."""


def split_documents(documents: list[str], chunk_size: int = 1200) -> list[str]:
    return [document[index:index + chunk_size] for document in documents for index in range(0, len(document), chunk_size)]