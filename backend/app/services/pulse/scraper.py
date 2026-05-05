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

from google_play_scraper import Sort, reviews as gps_reviews
from langdetect import detect
from supabase import Client, create_client

from app.config import settings
from app.core import audit
from app.core.pii import redact

log = logging.getLogger(__name__)

INDMONEY_APP_ID = "in.indwealth"  # Google Play app ID for INDmoney (legacy IndWealth package)
REVIEW_WINDOW_WEEKS = 10  # midpoint of 8-12 week spec window

_client: Client | None = None


def _supabase() -> Client:
    """Lazy singleton Supabase client."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def _as_utc(dt: datetime) -> datetime:
    """google-play-scraper returns naive datetimes (UTC). Make them tz-aware
    so they compare cleanly with our UTC-aware cutoff."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _is_valid_review(text: str) -> bool:
    """R-PULSE7: must be English and > 5 words."""
    words = text.split()
    if len(words) <= 5:
        return False
    try:
        return detect(text) == "en"
    except Exception:
        return False  # if detection fails, reject (safe default)


def _clamp_rating(raw: object) -> int | None:
    """Coerce a google-play-scraper score to a 1-5 integer; None if invalid."""
    if raw is None:
        return None
    try:
        rating = int(raw)
    except (TypeError, ValueError):
        return None
    if rating < 1 or rating > 5:
        return None
    return rating


async def scrape_reviews(trigger_source: str = "manual") -> dict:
    """Fetch INDMoney Play Store reviews, filter, dedup, write to DB.

    Args:
        trigger_source: 'manual' (admin button) or 'cron' (GitHub Actions).

    Returns:
        {
          "fetched": int,    # raw reviews fetched from Play Store
          "accepted": int,   # reviews that passed R-PULSE7
          "inserted": int,   # new rows written (after dedup)
          "filtered_out": int,  # rejected by R-PULSE7 or date window
        }
    """
    started_at = datetime.now(timezone.utc)

    try:
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
            if r.get("at") is not None and _as_utc(r["at"]) >= cutoff
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
            rating = _clamp_rating(r.get("score"))
            if rating is None:
                # Drop rows without a valid 1-5 rating (DB CHECK would reject them).
                continue
            clean_content = redact(r["content"].strip())
            rows.append({
                "play_review_id": r["reviewId"],
                "user_name": r.get("userName"),
                "rating": rating,
                "content": clean_content,
                "posted_at": _as_utc(r["at"]).isoformat(),
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

        # 6. Write audit row to scrape_runs (real schema)
        finished_at = datetime.now(timezone.utc)

        def _insert_audit() -> None:
            audit.record_scrape_run(
                _supabase(),
                started_at=started_at.isoformat(),
                finished_at=finished_at.isoformat(),
                status="ok",
                review_count=accepted,
                filtered_out_count=filtered_out,
                trigger_source=trigger_source,
                error_message=None,
            )

        await asyncio.to_thread(_insert_audit)
        log.info(
            "scrape_runs audit row written (status=ok, review_count=%d, filtered_out=%d, trigger=%s)",
            accepted,
            filtered_out,
            trigger_source,
        )

        # API/test contract: keep the legacy result dict shape.
        return {
            "fetched": fetched,
            "accepted": accepted,
            "inserted": inserted,
            "filtered_out": filtered_out,
        }
    except Exception as exc:
        # Best-effort error audit row; do not mask the original failure.
        finished_at = datetime.now(timezone.utc)
        try:
            def _insert_error_audit() -> None:
                audit.record_scrape_run(
                    _supabase(),
                    started_at=started_at.isoformat(),
                    finished_at=finished_at.isoformat(),
                    status="error",
                    review_count=0,
                    filtered_out_count=0,
                    trigger_source=trigger_source,
                    error_message=str(exc),
                )

            await asyncio.to_thread(_insert_error_audit)
        except Exception as audit_exc:  # pragma: no cover - defensive
            log.warning("Failed to write error audit row: %s", audit_exc)
        raise


def _cutoff_date() -> datetime:
    return datetime.now(timezone.utc) - timedelta(weeks=REVIEW_WINDOW_WEEKS)
