"""Tests for bootstrap_from_jsonl.

The bootstrap path replaces the network-fetch ingest in deployment
environments where the source URLs are geo-blocked.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.core import retriever as r_mod
from app.core.retriever import get_retriever
from app.services.rag.bootstrap import bootstrap_from_jsonl


def _isolated_retriever(tmp_path: Path, monkeypatch) -> "r_mod.Retriever":
    monkeypatch.setattr(r_mod, "CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(r_mod, "_singleton", None)
    retriever = get_retriever()
    retriever.reset()
    return retriever


def test_bootstrap_populates_empty_index(tmp_path: Path, monkeypatch) -> None:
    fixture = tmp_path / "corpus.jsonl"
    records = [
        {
            "id": "a-0",
            "text": "first chunk text",
            "metadata": {"url": "https://x.example/p1", "title": "P1", "category": "mf_factsheet", "chunk_index": 0},
        },
        {
            "id": "a-1",
            "text": "second chunk text",
            "metadata": {"url": "https://x.example/p1", "title": "P1", "category": "mf_factsheet", "chunk_index": 1},
        },
        {
            "id": "b-0",
            "text": "third chunk text",
            "metadata": {"url": "https://y.example/p2", "title": "P2", "category": "fee_scenario", "chunk_index": 0},
        },
    ]
    with fixture.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    retriever = _isolated_retriever(tmp_path, monkeypatch)

    n = bootstrap_from_jsonl(retriever, fixture)

    assert n == 3
    assert retriever.count() == 3
    assert retriever.indexed_urls() == {"https://x.example/p1", "https://y.example/p2"}

    monkeypatch.setattr(r_mod, "_singleton", None)


def test_bootstrap_missing_file_returns_zero(tmp_path: Path, monkeypatch) -> None:
    retriever = _isolated_retriever(tmp_path, monkeypatch)

    n = bootstrap_from_jsonl(retriever, tmp_path / "does-not-exist.jsonl")

    assert n == 0
    assert retriever.count() == 0

    monkeypatch.setattr(r_mod, "_singleton", None)


def test_bootstrap_skips_blank_lines(tmp_path: Path, monkeypatch) -> None:
    fixture = tmp_path / "corpus.jsonl"
    rec_a = {
        "id": "x-0",
        "text": "hello world",
        "metadata": {"url": "https://z.example/p", "title": "P", "category": "mf_factsheet", "chunk_index": 0},
    }
    rec_b = {
        "id": "x-1",
        "text": "second chunk",
        "metadata": {"url": "https://z.example/p", "title": "P", "category": "mf_factsheet", "chunk_index": 1},
    }
    with fixture.open("w", encoding="utf-8") as f:
        f.write(json.dumps(rec_a) + "\n")
        f.write("\n")
        f.write("   \n")
        f.write(json.dumps(rec_b) + "\n")

    retriever = _isolated_retriever(tmp_path, monkeypatch)

    n = bootstrap_from_jsonl(retriever, fixture)

    assert n == 2
    assert retriever.count() == 2
    assert retriever.indexed_urls() == {"https://z.example/p"}

    monkeypatch.setattr(r_mod, "_singleton", None)


def test_bootstrap_default_path_uses_data_corpus_jsonl(monkeypatch, tmp_path: Path) -> None:
    """Sanity: the default path resolves under backend/data/corpus.jsonl."""
    from app.services.rag.bootstrap import DEFAULT_PATH

    assert DEFAULT_PATH.name == "corpus.jsonl"
    assert DEFAULT_PATH.parent.name == "data"
    assert DEFAULT_PATH.parent.parent.name == "backend"
