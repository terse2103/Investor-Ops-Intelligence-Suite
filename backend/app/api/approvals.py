"""Pillar C: HITL Approval Center endpoints."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import require_admin
from app.services.approvals.dispatcher import decide_action, list_pending

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class DecisionIn(BaseModel):
    status: str  # "approved" | "rejected"


@router.get("/pending")
async def list_pending_endpoint(user: dict = Depends(require_admin)) -> dict:
    """Return all pending_actions joined with their parent call."""
    items = await asyncio.to_thread(list_pending)
    return {"items": items}


@router.post("/{action_id}/decide")
async def decide_endpoint(
    action_id: str,
    payload: DecisionIn,
    user: dict = Depends(require_admin),
) -> dict:
    """Approve or reject a pending action.

    On approve, dispatches by action type:
      calendar / sheets → core/google_api.py
      email             → core/mcp_client.py (Gmail MCP)
    Once all 3 actions for the booking are decided, the notifier fires once.
    """
    try:
        result = await asyncio.to_thread(
            decide_action,
            action_id,
            decision=payload.status,
            decided_by=user.get("id"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        log.exception("approval decide failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Approval dispatch failed: {exc}",
        ) from exc
    return result
