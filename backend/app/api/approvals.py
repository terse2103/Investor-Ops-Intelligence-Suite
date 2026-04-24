"""Pillar C: HITL Approval Center endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import require_admin

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class DecisionIn(BaseModel):
    status: str  # "approved" | "rejected"


@router.get("/pending")
async def list_pending(user: dict = Depends(require_admin)) -> dict:
    """Return all pending_actions where status='pending'."""
    return {"status": "not_implemented", "items": []}


@router.post("/{action_id}/decide")
async def decide(
    action_id: str,
    payload: DecisionIn,
    user: dict = Depends(require_admin),
) -> dict:
    """Approve or reject a pending action; dispatches downstream on approve.

    TODO (Day 5): on approve, dispatch by action type:
        calendar / sheets → core/google_api.py
        email             → core/mcp_client.py (Gmail MCP)
    Then, once all 3 actions for the booking are decided, trigger notifier.
    """
    return {"status": "not_implemented", "action_id": action_id}
