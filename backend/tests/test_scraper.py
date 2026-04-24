"""Unit tests for scrape_reviews() in services/pulse/scraper.py."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.services.pulse.scraper import REVIEW_WINDOW_WEEKS, scrape_reviews


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_review(
    review_id: str,
    content: str,
    score: int = 5,
    days_ago: int = 5,
) -> dict:
    """Build a fake google-play-scraper review dict."""
    return {
        "reviewId": review_id,
        "content": content,
        "score": score,
        "at": datetime.now(timezone.utc) - timedelta(days=days_ago),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_EN_REVIEW_1 = _make_review(
    "r1",
    "This app is absolutely great for managing investments easily",
    score=5,
    days_ago=3,
)
VALID_EN_REVIEW_2 = _make_review(
    "r2",
    "Really helpful for tracking mutual funds and stocks portfolio",
    score=4,
    days_ago=10,
)
# Too short (only 3 words) — filtered by _is_valid_review
SHORT_REVIEW = _make_review("r3", "Great app", score=5, days_ago=2)
# Very old review — filtered by date window
OLD_REVIEW = _make_review(
    "r4",
    "Used this app a long time ago and it was quite decent",
    score=3,
    days_ago=(REVIEW_WINDOW_WEEKS * 7) + 5,  # beyond window
)
# Non-English review (Hindi) — filtered by langdetect
HINDI_REVIEW = _make_review(
    "r5",
    "यह ऐप बहुत अच्छा है निवेश के लिए उपयोगी",
    score=4,
    days_ago=1,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scrape_reviews_counts_and_redact() -> None:
    """
    Given 5 reviews (2 valid English, 1 too-short, 1 too-old, 1 non-English),
    only the 2 valid ones should be accepted and upserted.
    Counts must reflect the full pipeline.
    """
    fake_reviews = [
        VALID_EN_REVIEW_1,
        VALID_EN_REVIEW_2,
        SHORT_REVIEW,
        OLD_REVIEW,
        HINDI_REVIEW,
    ]

    # Mock upsert response: return data for each inserted row
    mock_upsert_resp = MagicMock()
    mock_upsert_resp.data = [{"id": "uuid-1"}, {"id": "uuid-2"}]

    mock_insert_resp = MagicMock()
    mock_insert_resp.data = []

    # Build chained mock: table("x").upsert(...).execute() / .insert(...).execute()
    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_upsert_resp
    mock_table.insert.return_value.execute.return_value = mock_insert_resp

    mock_supabase_client = MagicMock()
    mock_supabase_client.table.return_value = mock_table

    with (
        patch(
            "app.services.pulse.scraper.gps_reviews" if False else "google_play_scraper.reviews",
            return_value=(fake_reviews, None),
        ) as mock_gps,
        patch(
            "app.services.pulse.scraper._supabase",
            return_value=mock_supabase_client,
        ),
        patch("langdetect.detect", side_effect=_fake_langdetect),
    ):
        result = await scrape_reviews()

    assert result["fetched"] == 5
    assert result["accepted"] == 2
    assert result["inserted"] == 2
    assert result["filtered_out"] == 3  # short + old + hindi


@pytest.mark.asyncio
async def test_scrape_reviews_redact_called_on_accepted() -> None:
    """redact() must be called exactly once per accepted review."""
    fake_reviews = [VALID_EN_REVIEW_1, VALID_EN_REVIEW_2, SHORT_REVIEW]

    mock_upsert_resp = MagicMock()
    mock_upsert_resp.data = [{"id": "uuid-1"}, {"id": "uuid-2"}]
    mock_insert_resp = MagicMock()
    mock_insert_resp.data = []

    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_upsert_resp
    mock_table.insert.return_value.execute.return_value = mock_insert_resp
    mock_supabase_client = MagicMock()
    mock_supabase_client.table.return_value = mock_table

    with (
        patch("google_play_scraper.reviews", return_value=(fake_reviews, None)),
        patch("app.services.pulse.scraper._supabase", return_value=mock_supabase_client),
        patch("langdetect.detect", side_effect=_fake_langdetect),
        patch("app.services.pulse.scraper.redact", wraps=lambda t: t) as mock_redact,
    ):
        result = await scrape_reviews()

    # Only 2 reviews pass (VALID_EN_REVIEW_1 and VALID_EN_REVIEW_2)
    assert mock_redact.call_count == 2
    called_contents = {c.args[0] for c in mock_redact.call_args_list}
    assert VALID_EN_REVIEW_1["content"] in called_contents
    assert VALID_EN_REVIEW_2["content"] in called_contents


@pytest.mark.asyncio
async def test_scrape_reviews_all_filtered_out() -> None:
    """When every review is filtered, upsert is skipped and counts are 0."""
    fake_reviews = [SHORT_REVIEW]  # fails _is_valid_review (too short)

    mock_insert_resp = MagicMock()
    mock_insert_resp.data = []
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_insert_resp
    mock_supabase_client = MagicMock()
    mock_supabase_client.table.return_value = mock_table

    with (
        patch("google_play_scraper.reviews", return_value=(fake_reviews, None)),
        patch("app.services.pulse.scraper._supabase", return_value=mock_supabase_client),
        patch("langdetect.detect", side_effect=_fake_langdetect),
    ):
        result = await scrape_reviews()

    assert result["fetched"] == 1
    assert result["accepted"] == 0
    assert result["inserted"] == 0
    assert result["filtered_out"] == 1

    # upsert must NOT have been called (no accepted rows)
    mock_table.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_scrape_reviews_audit_row_written() -> None:
    """A scrape_runs row must always be written, even when nothing is accepted."""
    fake_reviews = [SHORT_REVIEW]

    mock_insert_resp = MagicMock()
    mock_insert_resp.data = []
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = mock_insert_resp
    mock_supabase_client = MagicMock()
    mock_supabase_client.table.return_value = mock_table

    with (
        patch("google_play_scraper.reviews", return_value=(fake_reviews, None)),
        patch("app.services.pulse.scraper._supabase", return_value=mock_supabase_client),
        patch("langdetect.detect", side_effect=_fake_langdetect),
    ):
        result = await scrape_reviews()

    # The audit insert must have been called exactly once on "scrape_runs"
    scrape_runs_calls = [
        c for c in mock_supabase_client.table.call_args_list
        if c.args[0] == "scrape_runs"
    ]
    assert len(scrape_runs_calls) == 1

    # The inserted audit row must match the returned dict
    insert_args = mock_table.insert.call_args_list[-1].args[0]
    assert insert_args["fetched"] == result["fetched"]
    assert insert_args["accepted"] == result["accepted"]
    assert insert_args["inserted"] == result["inserted"]
    assert insert_args["filtered_out"] == result["filtered_out"]


@pytest.mark.asyncio
async def test_scrape_reviews_old_reviews_filtered_by_date() -> None:
    """Reviews beyond REVIEW_WINDOW_WEEKS must be excluded from accepted count."""
    fake_reviews = [VALID_EN_REVIEW_1, OLD_REVIEW]

    mock_upsert_resp = MagicMock()
    mock_upsert_resp.data = [{"id": "uuid-1"}]
    mock_insert_resp = MagicMock()
    mock_insert_resp.data = []
    mock_table = MagicMock()
    mock_table.upsert.return_value.execute.return_value = mock_upsert_resp
    mock_table.insert.return_value.execute.return_value = mock_insert_resp
    mock_supabase_client = MagicMock()
    mock_supabase_client.table.return_value = mock_table

    with (
        patch("google_play_scraper.reviews", return_value=(fake_reviews, None)),
        patch("app.services.pulse.scraper._supabase", return_value=mock_supabase_client),
        patch("langdetect.detect", side_effect=_fake_langdetect),
    ):
        result = await scrape_reviews()

    assert result["fetched"] == 2
    assert result["accepted"] == 1   # only VALID_EN_REVIEW_1 passes
    assert result["filtered_out"] == 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_langdetect(text: str) -> str:
    """Return 'en' for ASCII-dominant text, 'hi' for Devanagari."""
    # Simple heuristic: if most chars are ASCII letters, treat as English.
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters == 0:
        return "en"
    return "en" if ascii_letters / total_letters >= 0.8 else "hi"
