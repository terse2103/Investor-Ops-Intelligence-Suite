"""Pillar B: Weekly Product Pulse (M2 Part A)."""
from fastapi import APIRouter, Depends

from app.core.auth import require_admin, require_auth

router = APIRouter(prefix="/api/pulse", tags=["pulse"])


@router.post("/generate")
async def generate_pulse(user: dict = Depends(require_admin)) -> dict:
    """Generate a pulse from reviews in the last 8-12 weeks.

    TODO (Day 3): load reviews, cluster into max 5 themes, pick top 3, extract
    3 quotes, write ≤250-word note with 3 actions, persist pulse and update current_themes.
    """
    return {"status": "not_implemented"}


@router.get("/latest")
async def latest_pulse(user: dict = Depends(require_auth)) -> dict:
    """Return the most recent pulse + its top 3 themes."""
    return {"status": "not_implemented"}
