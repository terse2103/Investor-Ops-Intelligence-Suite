"""Pluggable retriever interface. Day-2 impl: Chroma + sentence-transformers MiniLM."""
from typing import Protocol


class Retriever(Protocol):
    """Swap Chroma for pgvector later without touching callers."""

    def ingest(self, sources: list[dict]) -> None:
        """Embed and upsert source chunks into the vector store."""

    def query(self, question: str, top_k: int = 8) -> list[dict]:
        """Return top_k most relevant chunks. Default 8 to compensate for MiniLM."""


# TODO (Day 2): implement ChromaRetriever using sentence-transformers/all-MiniLM-L6-v2.
# File-backed persistence at backend/chroma_data/. Re-ingest on startup because
# Render free tier does not guarantee disk persistence across redeploys.
