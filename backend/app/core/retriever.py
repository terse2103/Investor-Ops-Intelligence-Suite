"""Chroma-backed retriever using sentence-transformers all-MiniLM-L6-v2."""
from __future__ import annotations

import logging
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

log = logging.getLogger(__name__)

CHROMA_DIR = Path(__file__).resolve().parent.parent.parent / "chroma_data"
COLLECTION_NAME = "indmoney_corpus"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Retriever:
    """Thin wrapper over Chroma for RAG ingest + query.

    Swap Chroma for pgvector later without touching callers (see spec §6.2).
    """

    def __init__(self) -> None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._embed = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL,
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self._embed
        )

    def count(self) -> int:
        return self._collection.count()

    def indexed_urls(self) -> set[str]:
        """Return the set of unique source URLs already in the index.

        Used by the startup ingest to ingest only sources that are missing,
        so adding a new source to the corpus seed list and restarting the
        backend automatically picks it up without wiping the existing index.
        """
        if self._collection.count() == 0:
            return set()
        res = self._collection.get(include=["metadatas"])
        metas = res.get("metadatas") or []
        return {m["url"] for m in metas if m and m.get("url")}

    def reset(self) -> None:
        """Drop and recreate the collection. Used by tests."""
        try:
            self._client.delete_collection(name=COLLECTION_NAME)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=self._embed
        )

    def ingest(self, chunks: list[dict]) -> None:
        """Upsert chunks. Each chunk has keys: id, text, metadata (dict)."""
        if not chunks:
            return
        self._collection.upsert(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[c["metadata"] for c in chunks],
        )
        log.info("Indexed %d chunks into %s", len(chunks), COLLECTION_NAME)

    def query(self, question: str, top_k: int = 8) -> list[dict]:
        """Return top_k most relevant chunks with text + metadata + distance."""
        if self._collection.count() == 0:
            return []
        res = self._collection.query(query_texts=[question], n_results=top_k)
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        return [
            {"text": d, "metadata": m, "distance": dist}
            for d, m, dist in zip(docs, metas, dists)
        ]


_singleton: Retriever | None = None


def get_retriever() -> Retriever:
    global _singleton
    if _singleton is None:
        _singleton = Retriever()
    return _singleton
