"""Scrape endpoint: manual trigger (admin button) and GitHub Actions cron."""
from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import settings
from app.core.auth import require_auth
from app.services.pulse.scraper import scrape_reviews

router = APIRouter(prefix="/api", tags=["scrape"])


async def _scrape_auth(
    x_scrape_secret: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Allow either the GitHub Actions shared secret OR an admin JWT."""
    if x_scrape_secret is not None:
        if (
            not settings.scrape_shared_secret
            or x_scrape_secret != settings.scrape_shared_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid scrape secret",
            )
        return
    user = await require_auth(authorization)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.post("/scrape")
async def scrape(auth: None = Depends(_scrape_auth)) -> dict:
    """Trigger a scrape of INDMoney Play Store reviews.

    Requires either an admin-role JWT (via /admin UI) OR the shared-secret header
    (from GitHub Actions cron). Applies R-PULSE7 (English + >5 words) at ingest.
    """
    return await scrape_reviews()
