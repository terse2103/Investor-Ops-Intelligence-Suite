"""Fetch INDMoney pages, extract text, chunk, index into Chroma."""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.core.pii import redact
from app.core.retriever import get_retriever

log = logging.getLogger(__name__)

CHUNK_SIZE_CHARS = 1200  # ~300 tokens
CHUNK_OVERLAP = 200
USER_AGENT = "InvestorOpsSuite/0.1 (Capstone RAG crawler)"


async def ingest_sources(sources: list[dict]) -> int:
    """Fetch each source URL, chunk the text, upsert into Chroma.

    Returns the number of chunks ingested.
    """
    retriever = get_retriever()
    total = 0
    async with httpx.AsyncClient(
        timeout=30.0, headers={"User-Agent": USER_AGENT}
    ) as client:
        for src in sources:
            try:
                raw = await _fetch_and_extract(client, src["url"])
            except Exception as e:
                log.warning("Failed to fetch %s: %s", src["url"], e)
                continue
            text = redact(raw)  # R-SCRAPE2 / R-G2 at ingestion
            chunks = _chunk_text(text, CHUNK_SIZE_CHARS, CHUNK_OVERLAP)
            fetched_at = datetime.now(timezone.utc).date().isoformat()
            payload = [
                {
                    "id": _chunk_id(src["url"], idx),
                    "text": chunk,
                    "metadata": {
                        "url": src["url"],
                        "title": src["title"],
                        "category": src["category"],
                        "chunk_index": idx,
                        "fetched_at": fetched_at,
                    },
                }
                for idx, chunk in enumerate(chunks)
            ]
            retriever.ingest(payload)
            total += len(payload)
            log.info("%s: %d chunks", src["title"], len(payload))
    return total


async def _fetch_and_extract(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _chunk_id(url: str, idx: int) -> str:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"{h}-{idx}"
