"""Approval dispatcher: applies admin decisions and runs downstream actions.

R-APPROVE1: external action only fires on approve.
R-APPROVE3: every execution writes an action_audit row (success or failure).
R-APPROVE4: when all 3 actions on a call are decided, the notifier fires once.

Tests should patch `_supabase`, `google_api`, `mcp_client`, and `notifier`.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.config import settings
from app.core import google_api, mcp_client, notifier

log = logging.getLogger(__name__)

VALID_DECISIONS = {"approved", "rejected"}

_client: Client | None = None


def _supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def list_pending() -> list[dict[str, Any]]:
    """Return pending_actions joined with the parent call for the admin queue."""
    resp = (
        _supabase()
        .table("pending_actions")
        .select("*, calls!pending_actions_call_id_fkey(id,user_id,booking_code,topic,started_at)")
        .eq("status", "pending")
        .order("created_at", desc=False)
        .execute()
    )
    return resp.data or []


def _get_action(action_id: str) -> dict[str, Any] | None:
    resp = (
        _supabase()
        .table("pending_actions")
        .select("*")
        .eq("id", action_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def _get_call(call_id: str) -> dict[str, Any] | None:
    resp = _supabase().table("calls").select("*").eq("id", call_id).limit(1).execute()
    rows = resp.data or []
    return rows[0] if rows else None


def _all_actions_for_call(call_id: str) -> list[dict[str, Any]]:
    resp = (
        _supabase()
        .table("pending_actions")
        .select("type,status")
        .eq("call_id", call_id)
        .execute()
    )
    return resp.data or []


def _execute_action(action: dict[str, Any], to_email: str | None) -> tuple[str, dict[str, Any] | None, str | None]:
    """Run the downstream side-effect for an approved action.

    Returns (status, provider_response, error_message).
    status is one of: 'executed', 'failed'.
    """
    kind = action.get("type")
    payload = action.get("payload") or {}
    try:
        if kind == "calendar":
            resp = google_api.create_tentative_event(payload=payload)
            return "executed", _truncate(resp), None
        if kind == "sheets":
            resp = google_api.append_booking_row(payload=payload)
            return "executed", _truncate(resp), None
        if kind == "email":
            if not to_email:
                return "failed", None, "no recipient email configured for booking user"
            resp = asyncio.run(mcp_client.create_draft(payload=payload, to=to_email))
            return "executed", _truncate(resp), None
        return "failed", None, f"unknown action type: {kind}"
    except Exception as exc:
        log.exception("dispatch failed for action %s (type=%s): %s", action.get("id"), kind, exc)
        return "failed", None, str(exc)


def _truncate(obj: Any, limit: int = 4096) -> dict[str, Any]:
    """Coerce an arbitrary provider response into a JSON-serialisable dict."""
    try:
        import json

        s = json.dumps(obj, default=str)
        if len(s) > limit:
            s = s[:limit] + "...<truncated>"
        return {"raw": s}
    except Exception:  # pragma: no cover - defensive
        return {"raw": str(obj)[:limit]}


def _user_email_for_call(call: dict[str, Any] | None) -> str | None:
    if not call:
        return None
    user_id = call.get("user_id")
    if not user_id:
        return None
    try:
        resp = (
            _supabase()
            .table("user_contacts")
            .select("email")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        log.warning("user_contacts lookup failed: %s", exc)
        return None
    rows = resp.data or []
    return rows[0]["email"] if rows else None


def decide_action(action_id: str, *, decision: str, decided_by: str | None) -> dict[str, Any]:
    """Apply admin decision; on approve, run the downstream action.

    Returns a result dict for the API response.
    """
    if decision not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of {VALID_DECISIONS}")

    action = _get_action(action_id)
    if not action:
        raise ValueError(f"pending_action {action_id} not found")
    if action.get("status") != "pending":
        raise ValueError(f"action {action_id} is already {action.get('status')}")

    now = datetime.now(timezone.utc).isoformat()
    update_payload: dict[str, Any] = {
        "status": decision,
        "decided_at": now,
        "decided_by": decided_by,
    }

    audit_row: dict[str, Any] | None = None
    exec_status: str | None = None

    if decision == "approved":
        call = _get_call(action["call_id"])
        to_email = _user_email_for_call(call)
        exec_status, provider_response, err = _execute_action(action, to_email)
        update_payload["status"] = "executed" if exec_status == "executed" else "failed"
        update_payload["executed_at"] = now
        audit_row = {
            "pending_action_id": action_id,
            "status": "ok" if exec_status == "executed" else "failed",
            "provider_response": provider_response,
            "error_message": err,
        }
    else:
        # rejected: no execution, no audit row (only successful/failed runs are audited).
        pass

    _supabase().table("pending_actions").update(update_payload).eq("id", action_id).execute()
    if audit_row is not None:
        _supabase().table("action_audit").insert(audit_row).execute()

    notification = _maybe_notify(action["call_id"])

    return {
        "action_id": action_id,
        "decision": decision,
        "execution_status": exec_status,
        "notification": notification,
    }


def _maybe_notify(call_id: str) -> dict[str, Any] | None:
    """If all 3 actions are now in a terminal state, fire the notifier once.

    Terminal states: executed, failed, rejected. ('approved' is transient — the
    dispatcher always advances it to executed/failed in the same transaction.)
    """
    actions = _all_actions_for_call(call_id)
    terminal = {"executed", "failed", "rejected"}
    if not actions or any(a.get("status") not in terminal for a in actions):
        return None

    # Only notify the first time we cross the line. Existing notifications_sent
    # row for this call is the marker.
    existing = (
        _supabase()
        .table("notifications_sent")
        .select("id")
        .eq("call_id", call_id)
        .limit(1)
        .execute()
    )
    if (existing.data or []):
        return {"status": "already_sent"}

    call = _get_call(call_id)
    if not call:
        return {"status": "call_not_found"}

    return notifier.notify_booking_decision(
        user_id=call.get("user_id"),
        call_id=call_id,
        booking_code=call.get("booking_code") or "?",
        topic=call.get("topic"),
        actions=actions,
    )
