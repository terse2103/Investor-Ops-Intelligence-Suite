"""Pillars B + C: Voice agent webhooks (Vapi → FastAPI)."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.config import settings
from app.core.auth import require_auth
from app.services.voice.context import (
    load_current_themes,
    to_vapi_date_variables,
    to_vapi_variables,
)
from app.services.voice.post_call import generate_booking_code

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/context")
async def call_context(user: dict = Depends(require_auth)) -> dict:
    """Return current_themes formatted as Vapi dynamic variables.

    Called by /user/voice just before starting a Vapi call. Variables are
    injected into the assistant's system prompt template (R-VOICE2).
    Degrades gracefully to empty strings when no pulse has been generated.

    Each request also mints a fresh NL-XXXX booking code (R-VOICE6) so the
    assistant can read out a unique, authoritative code on the call instead
    of hallucinating one. The frontend echoes this back in the call metadata
    so the post-call webhook persists the same code the caller heard.
    """
    themes = await asyncio.to_thread(load_current_themes)
    booking_code = generate_booking_code()
    return {
        "themes": themes,
        "booking_code": booking_code,
        "variables": {
            **to_vapi_variables(themes),
            **to_vapi_date_variables(),
            "booking_code": booking_code,
        },
    }


async def _verify_webhook_secret(
    x_vapi_secret: str | None = Header(default=None),
) -> None:
    """Vapi webhooks authenticate via a shared secret in a request header.

    The secret is set in the Vapi assistant config and matches
    settings.vapi_webhook_secret on the backend. Missing or wrong → 401.
    """
    expected = settings.vapi_webhook_secret
    if not expected:
        log.error("VAPI_WEBHOOK_SECRET not configured; rejecting webhook")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook authentication not configured on server",
        )
    if x_vapi_secret != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Vapi webhook secret",
        )


# Vapi sends many message types per call (status-update, transcript, hang, etc.).
# Only end-of-call-report carries the final analysis/structuredData we persist.
# Non-final events return 200 immediately so Vapi doesn't retry, but we don't
# write rows for them.
FINAL_VAPI_MESSAGE_TYPE = "end-of-call-report"


@router.post("/post-call")
async def post_call(
    request: Request,
    _: None = Depends(_verify_webhook_secret),
) -> dict:
    """Vapi post-call webhook. Persists the call and queues 3 pending_actions.

    The handler:
      1. Filters non-final Vapi events (status-update, transcript, hang) -> noop
      2. Parses Vapi payload (call id, transcript, user_id, topic, slot)
      3. PII-guards transcript before persistence (R-VOICE4 safety net)
      4. Generates booking code NL-XXXX (R-VOICE6)
      5. Writes calls row + 3 pending_actions (idempotent on call_id)
      6. Email payload includes Market Context from latest pulse (R-APPROVE2)
    """
    from app.services.voice.post_call import handle_post_call

    payload = await request.json()
    msg = payload.get("message") if isinstance(payload.get("message"), dict) else payload
    msg_type = (msg or {}).get("type")
    # Tracing: append every message type we see to /tmp/vapi_types.log so the
    # operator can audit what Vapi is sending without needing app-level logging
    # turned on. Cheap, append-only, no performance impact at demo scale.
    try:
        with open("/tmp/vapi_types.log", "a", encoding="utf-8") as f:
            f.write(f"{msg_type}\n")
    except Exception:
        pass
    if msg_type != FINAL_VAPI_MESSAGE_TYPE:
        log.info("post-call: skipping non-final Vapi event type=%s", msg_type)
        return {"skipped": True, "type": msg_type}

    try:
        result = await asyncio.to_thread(handle_post_call, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        log.exception("post-call webhook failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Post-call processing failed: {exc}",
        ) from exc
    return result
