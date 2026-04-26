"""Pillar B: Weekly Product Pulse (M2 Part A)."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import require_admin, require_auth
from app.services.pulse.generator import generate_pulse, load_latest_pulse

router = APIRouter(prefix="/api/pulse", tags=["pulse"])


@router.post("/generate")
async def generate_pulse_endpoint(user: dict = Depends(require_admin)) -> dict:
    """Generate a pulse from reviews in the last 8-12 weeks.

    Clusters into max 5 themes, surfaces top 3, picks 3 quotes, writes a
    ≤250-word note with 3 actions, persists to pulses, and refreshes
    current_themes for Vapi injection.
    """
    try:
        pulse = await generate_pulse()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return pulse


@router.get("/latest")
async def latest_pulse_endpoint(user: dict = Depends(require_auth)) -> dict:
    """Return the most recent pulse + its top 3 themes."""
    row = await asyncio.to_thread(load_latest_pulse)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no pulse generated yet",
        )
    return row
