"""Booking-decision notifier (R-APPROVE4).

Sends exactly ONE email to the booking user once all three pending_actions for
their call have been decided (any mix of approve/reject). Provider is Resend by
default (HTTP API only, no SDK). The provider is pluggable via the `_send_email`
function: swap to SendGrid / SES / SMTP by replacing that single function.

The notifier reads the user's email from `user_contacts`. If the user never
saved a notification email, we still write a `notifications_sent` row with
status=`skipped_no_contact` so the audit is complete.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from supabase import Client, create_client

from app.config import settings

log = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"

_client: Client | None = None


def _supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def _user_email(user_id: str | None) -> str | None:
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
    if not rows:
        return None
    return rows[0].get("email")


def _decision_summary(actions: list[dict[str, Any]]) -> str:
    """Map (type, status) tuples into a one-line summary for the email body."""
    parts: list[str] = []
    by_type = {a.get("type"): a.get("status") for a in actions}
    for kind in ("calendar", "sheets", "email"):
        status = by_type.get(kind, "unknown")
        parts.append(f"{kind}={status}")
    return "; ".join(parts)


def build_email(
    *,
    booking_code: str,
    actions: list[dict[str, Any]],
    topic: str | None,
) -> dict[str, str]:
    """Craft the subject + body for the user-facing notification."""
    summary = _decision_summary(actions)
    approved_count = sum(1 for a in actions if a.get("status") == "approved")
    if approved_count == len(actions):
        verb = "approved"
    elif approved_count == 0:
        verb = "rejected"
    else:
        verb = "partially approved"

    subject = f"Booking {booking_code}: {verb}"
    body = (
        f"Hi,\n\n"
        f"Your advisor consultation booking ({booking_code}) has been {verb}.\n"
        f"Topic: {topic or 'general'}\n"
        f"Decision summary: {summary}\n\n"
        f"You will receive a follow-up from the advisor team if applicable.\n\n"
        f"Investor Ops"
    )
    return {"subject": subject, "body": body}


def _send_email(*, to: str, subject: str, body: str) -> dict[str, Any]:
    """Provider call. Resend HTTP API; swap for SendGrid/SES if needed."""
    api_key = settings.resend_api_key or settings.email_api_key
    if not api_key:
        raise RuntimeError("RESEND_API_KEY (or EMAIL_API_KEY) not configured")
    sender = settings.email_from
    if not sender:
        raise RuntimeError("EMAIL_FROM not configured")
    resp = httpx.post(
        RESEND_ENDPOINT,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"from": sender, "to": [to], "subject": subject, "text": body},
        timeout=20.0,
    )
    resp.raise_for_status()
    return resp.json()


def notify_booking_decision(
    *,
    user_id: str | None,
    call_id: str,
    booking_code: str,
    topic: str | None,
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Send one notification per booking. Always writes a notifications_sent row.

    Returns {"status": ..., "email": ..., "provider": ..., "skipped": bool}.
    """
    to = _user_email(user_id)
    if not to:
        log.info(
            "notifier.skipped_no_contact user_id=%s booking=%s",
            user_id,
            booking_code,
        )
        _audit(user_id=user_id, call_id=call_id, status="skipped_no_contact", provider_response=None)
        return {"status": "skipped_no_contact", "skipped": True}

    msg = build_email(booking_code=booking_code, actions=actions, topic=topic)
    try:
        provider_response = _send_email(to=to, subject=msg["subject"], body=msg["body"])
    except httpx.HTTPError as exc:
        log.warning("notifier.provider_error booking=%s err=%s", booking_code, exc)
        _audit(
            user_id=user_id,
            call_id=call_id,
            status="provider_error",
            provider_response={"error": str(exc)},
        )
        return {"status": "provider_error", "error": str(exc), "skipped": False}

    _audit(
        user_id=user_id,
        call_id=call_id,
        status="sent",
        provider_response=provider_response,
    )
    return {
        "status": "sent",
        "email": to,
        "provider": "resend",
        "provider_response": provider_response,
        "skipped": False,
    }


def _audit(
    *,
    user_id: str | None,
    call_id: str,
    status: str,
    provider_response: dict[str, Any] | None,
) -> None:
    """Insert a notifications_sent audit row."""
    try:
        _supabase().table("notifications_sent").insert(
            {
                "user_id": user_id,
                "call_id": call_id,
                "status": status,
                "provider_response": provider_response,
            }
        ).execute()
    except Exception as exc:
        log.warning("notifications_sent audit insert failed: %s", exc)
