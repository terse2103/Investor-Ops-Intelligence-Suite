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

import logging
from datetime import datetime, timedelta, timezone

from app.core.pii import redact

log = logging.getLogger(__name__)

INDMONEY_APP_ID = "in.indmoney"  # Google Play app ID for INDMoney
REVIEW_WINDOW_WEEKS = 10  # midpoint of 8-12 week spec window


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
          "filtered_out": int,  # rejected by R-PULSE7
        }

    TODO (Day 3):
    1. Call google_play_scraper.reviews() with count=200, lang="en", country="in"
    2. Compute cutoff date = now() - REVIEW_WINDOW_WEEKS weeks
    3. Filter out reviews older than cutoff
    4. Apply _is_valid_review() for R-PULSE7
    5. For each passing review: redact(content) for R-SCRAPE2
    6. Upsert into Supabase `reviews` table with dedup on review_id (R-SCRAPE1)
    7. Write a `scrape_runs` audit row with fetched/accepted/inserted/filtered_out counts
    """
    raise NotImplementedError("scrape_reviews is implemented on Day 3")


def _cutoff_date() -> datetime:
    return datetime.now(timezone.utc) - timedelta(weeks=REVIEW_WINDOW_WEEKS)
