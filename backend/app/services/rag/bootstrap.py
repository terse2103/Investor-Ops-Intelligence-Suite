"""Bootstrap the RAG index from a shipped JSONL fixture.

indmoney.com geo-blocks non-Indian IPs at the Cloudflare edge, so the
deployment environments (HF Spaces, GitHub Actions runners) cannot reach
the M1 fund-factsheet URLs. The startup ingest in app.main therefore
populates the index from this committed JSONL fixture rather than from
the live URLs.

Generate the JSONL with ``backend/scripts/dump_corpus.py`` after refreshing
the local Chroma index from a network position that can reach the sources.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.retriever import Retriever

log = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "corpus.jsonl"


def bootstrap_from_jsonl(
    retriever: Retriever, path: Path | None = None
) -> int:
    """Read JSONL records and upsert them into the retriever.

    Returns the number of chunks ingested. Returns 0 if the fixture file is
    missing (so deploys without a shipped corpus still start cleanly).
    """
    fixture = path or DEFAULT_PATH
    if not fixture.exists():
        log.info("Bootstrap fixture missing at %s; skipping", fixture)
        return 0

    chunks: list[dict] = []
    with fixture.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            chunks.append(
                {
                    "id": record["id"],
                    "text": record["text"],
                    "metadata": record.get("metadata", {}),
                }
            )

    if chunks:
        retriever.ingest(chunks)
        log.info("Bootstrapped %d chunks from %s", len(chunks), fixture)
    return len(chunks)
