"""Pillars B + C: Voice agent webhooks (Vapi → FastAPI)."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/context")
async def call_context() -> dict:
    """Return current_themes for Vapi dynamic-variable injection at call start.

    TODO (Day 4): read singleton row from current_themes table.
    """
    return {"status": "not_implemented"}


@router.post("/post-call")
async def post_call(request: Request) -> dict:
    """Vapi post-call webhook. Writes the 3 pending_actions per booking.

    TODO (Day 4-5): parse Vapi payload, PII-guard the transcript, write calls row,
    write 3 pending_actions (calendar/sheets/email) with Market Context injection
    into the email payload.
    """
    return {"status": "not_implemented"}
