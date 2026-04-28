"""Pillars B + C: Voice agent webhooks (Vapi → FastAPI)."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.config import settings
from app.core.auth import require_auth
from app.services.voice.context import load_current_themes, to_vapi_variables

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/context")
async def call_context(user: dict = Depends(require_auth)) -> dict:
    """Return current_themes formatted as Vapi dynamic variables.

    Called by /user/voice just before starting a Vapi call. Variables are
    injected into the assistant's system prompt template (R-VOICE2).
    Degrades gracefully to empty strings when no pulse has been generated.
    """
    themes = await asyncio.to_thread(load_current_themes)
    return {
        "themes": themes,
        "variables": to_vapi_variables(themes),
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


@router.post("/post-call")
async def post_call(
    request: Request,
    _: None = Depends(_verify_webhook_secret),
) -> dict:
    """Vapi post-call webhook. Persists the call and queues 3 pending_actions.

    The handler:
      1. Parses Vapi payload (call id, transcript, user_id, topic, slot)
      2. PII-guards transcript before persistence (R-VOICE4 safety net)
      3. Generates booking code NL-XXXX (R-VOICE6)
      4. Writes calls row + 3 pending_actions
      5. Email payload includes Market Context from latest pulse (R-APPROVE2)
    """
    from app.services.voice.post_call import handle_post_call

    payload = await request.json()
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
