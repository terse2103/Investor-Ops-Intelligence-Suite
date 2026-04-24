"""Play Store review scraper for INDMoney (services/pulse/scraper.py).

Triggered by POST /api/scrape from either:
  - Admin "Refresh now" button (via Supabase JWT)
  - GitHub Actions weekly cron (via SCRAPE_SHARED_SECRET header)

R-PULSE7 filter: accept only English reviews with > 5 words.
R-SCRAPE1: dedup on play_review_id.
R-SCRAPE2: PII guard on every inbound review.
R-SCRAPE3: window is reviews from the last 8-12 weeks.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from supabase import Client, create_client

from app.config import settings
from app.core.pii import redact

log = logging.getLogger(__name__)

INDMONEY_APP_ID = "in.indmoney"  # Google Play app ID for INDMoney
REVIEW_WINDOW_WEEKS = 10  # midpoint of 8-12 week spec window

_client: Client | None = None


def _supabase() -> Client:
    """Lazy singleton Supabase client."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def _is_valid_review(text: str) -> bool:
    """R-PULSE7: must be English and > 5 words."""
    words = text.split()
    if len(words) <= 5:
        return False
    try:
        from langdetect import detect
        return detect(text) == "en"
    except Exception:
        return False  # if detection fails, reject (safe default)


async def scrape_reviews() -> dict:
    """Fetch INDMoney Play Store reviews, filter, dedup, write to DB.

    Returns:
        {
          "fetched": int,    # raw reviews fetched from Play Store
          "accepted": int,   # reviews that passed R-PULSE7
          "inserted": int,   # new rows written (after dedup)
          "filtered_out": int,  # rejected by R-PULSE7 or date window
        }
    """
    from google_play_scraper import Sort, reviews as gps_reviews

    # 1. Fetch raw reviews from Play Store
    raw_reviews, _ = await asyncio.to_thread(
        gps_reviews,
        INDMONEY_APP_ID,
        lang="en",
        country="in",
        sort=Sort.NEWEST,
        count=200,
    )

    fetched = len(raw_reviews)
    log.info("Fetched %d raw reviews from Play Store", fetched)

    # 2. Apply date window filter (R-SCRAPE3)
    cutoff = _cutoff_date()
    window_filtered = [
        r for r in raw_reviews
        if r.get("at") is not None and r["at"] >= cutoff
    ]
    log.info(
        "After date window filter (%d weeks): %d reviews remain",
        REVIEW_WINDOW_WEEKS,
        len(window_filtered),
    )

    # 3. Apply R-PULSE7: English + > 5 words
    accepted_reviews = []
    for r in window_filtered:
        content = (r.get("content") or "").strip()
        if content and _is_valid_review(content):
            accepted_reviews.append(r)

    accepted = len(accepted_reviews)
    filtered_out = fetched - accepted
    log.info("Accepted %d reviews after R-PULSE7 filter (%d filtered out)", accepted, filtered_out)

    # 4. Redact PII (R-SCRAPE2) and build upsert rows
    rows = []
    for r in accepted_reviews:
        clean_content = redact(r["content"].strip())
        rows.append({
            "play_review_id": r["reviewId"],
            "content": clean_content,
            "score": r.get("score"),
            "at": r["at"].isoformat(),
        })

    # 5. Upsert into Supabase `reviews` table with dedup on play_review_id (R-SCRAPE1)
    inserted = 0
    if rows:
        def _upsert_reviews() -> int:
            resp = (
                _supabase()
                .table("reviews")
                .upsert(rows, on_conflict="play_review_id")
                .execute()
            )
            return len(resp.data) if resp.data else 0

        inserted = await asyncio.to_thread(_upsert_reviews)
        log.info("Upserted %d rows into reviews table", inserted)

    # 6. Write audit row to scrape_runs
    audit_row = {
        "fetched": fetched,
        "accepted": accepted,
        "inserted": inserted,
        "filtered_out": filtered_out,
    }

    def _insert_audit() -> None:
        _supabase().table("scrape_runs").insert(audit_row).execute()

    await asyncio.to_thread(_insert_audit)
    log.info("Audit row written: %s", audit_row)

    return audit_row


def _cutoff_date() -> datetime:
    return datetime.now(timezone.utc) - timedelta(weeks=REVIEW_WINDOW_WEEKS)
