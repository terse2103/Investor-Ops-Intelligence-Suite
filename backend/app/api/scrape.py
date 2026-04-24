"""Scrape endpoint: manual trigger (admin button) and GitHub Actions cron."""
from fastapi import APIRouter, Header, HTTPException, status

router = APIRouter(prefix="/api", tags=["scrape"])


@router.post("/scrape")
async def scrape(x_scrape_secret: str | None = Header(default=None)) -> dict:
    """Trigger a scrape of INDMoney Play Store reviews.

    Requires either an admin-role JWT (via /admin UI) OR the shared-secret header
    (from GitHub Actions cron). Applies R-PULSE7 (English + >5 words) at ingest.

    TODO (Day 3): auth check; call google-play-scraper; PII guard each review;
    dedup on play_review_id; write scrape_runs row with filtered_out_count.
    """
    # TODO: validate admin JWT or shared secret; 401 otherwise.
    return {"status": "not_implemented"}
