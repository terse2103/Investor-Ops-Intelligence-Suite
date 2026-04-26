"""Sanity tests for the RAG corpus seed list."""
from app.services.rag.corpus import (
    ALL_SOURCES,
    FEE_EXPLAINER_DOCS,
    NIPPON_INDIA_SCHEMES,
)

VALID_CATEGORIES = {"mf_factsheet", "fee_scenario", "other"}


def test_all_sources_combines_both_lists() -> None:
    assert len(ALL_SOURCES) == len(NIPPON_INDIA_SCHEMES) + len(FEE_EXPLAINER_DOCS)


def test_fee_docs_use_fee_scenario_category() -> None:
    assert FEE_EXPLAINER_DOCS, "FEE_EXPLAINER_DOCS must not be empty"
    for doc in FEE_EXPLAINER_DOCS:
        assert doc["category"] == "fee_scenario"


def test_every_source_has_required_keys_and_valid_category() -> None:
    for src in ALL_SOURCES:
        assert "url" in src and src["url"].startswith("http")
        assert "title" in src and src["title"]
        assert src["category"] in VALID_CATEGORIES


def test_urls_are_unique() -> None:
    urls = [s["url"] for s in ALL_SOURCES]
    assert len(urls) == len(set(urls))
