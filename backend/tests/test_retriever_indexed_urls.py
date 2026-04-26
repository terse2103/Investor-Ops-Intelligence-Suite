"""Sanity tests for Retriever.indexed_urls() and the missing-source diff logic."""
from __future__ import annotations

from app.core.retriever import get_retriever


def test_indexed_urls_returns_unique_urls(tmp_path, monkeypatch) -> None:
    # Use a fresh per-test Chroma directory so we don't pollute the dev index.
    from app.core import retriever as r_mod

    monkeypatch.setattr(r_mod, "CHROMA_DIR", tmp_path)
    monkeypatch.setattr(r_mod, "_singleton", None)

    retriever = get_retriever()
    retriever.reset()

    assert retriever.indexed_urls() == set()
    assert retriever.count() == 0

    retriever.ingest(
        [
            {
                "id": "a-0",
                "text": "alpha chunk one",
                "metadata": {"url": "https://a.example/page", "title": "A", "fetched_at": "2026-04-01"},
            },
            {
                "id": "a-1",
                "text": "alpha chunk two",
                "metadata": {"url": "https://a.example/page", "title": "A", "fetched_at": "2026-04-01"},
            },
            {
                "id": "b-0",
                "text": "beta chunk",
                "metadata": {"url": "https://b.example/page", "title": "B", "fetched_at": "2026-04-02"},
            },
        ]
    )

    assert retriever.indexed_urls() == {
        "https://a.example/page",
        "https://b.example/page",
    }
    assert retriever.count() == 3

    # Reset singleton so other tests don't see this temp index
    monkeypatch.setattr(r_mod, "_singleton", None)
