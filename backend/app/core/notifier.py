"""Booking-decision notifier (R-APPROVE4).

Sends exactly ONE email to the booking user once all three pending_actions for
their call have been decided (any mix of approve/reject). Provider is Resend by
default (HTTP API only, no SDK). The provider is pluggable via the `_send_email`
function: swap to SendGrid / SES / SMTP by replacing that single function.

The body states topic + IST slot date/time + booking code. Market context is
deliberately omitted here — that goes only in the advisor's Gmail draft (built
in services/voice/post_call.py).

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
from app.core import audit
from app.core.email_template import render_card
from app.services.voice.post_call import format_slot_ist

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


def _slot_iso_from_actions(actions: list[dict[str, Any]]) -> str:
    """Pull the ISO slot off the calendar action's payload (best-effort)."""
    for a in actions:
        if a.get("type") != "calendar":
            continue
        payload = a.get("payload") or {}
        slot = payload.get("start_iso") or payload.get("slot_iso") or ""
        if slot:
            return str(slot)
    # Sheets action also stores slot_iso; fall back to it for completeness.
    for a in actions:
        if a.get("type") != "sheets":
            continue
        payload = a.get("payload") or {}
        slot = payload.get("slot_iso") or ""
        if slot:
            return str(slot)
    return ""


def _verdict(actions: list[dict[str, Any]]) -> str:
    """One of: 'approved', 'rejected', 'partially approved' based on action statuses.

    Treats 'executed' as approved (the dispatcher promotes 'approved' → 'executed'
    after the side-effect runs) and 'failed' as approved-but-broken (still counts
    toward the user-facing 'approved' verdict — the booking decision was yes).
    """
    approved_states = {"approved", "executed", "failed"}
    approved_count = sum(1 for a in actions if a.get("status") in approved_states)
    if approved_count == len(actions):
        return "approved"
    if approved_count == 0:
        return "rejected"
    return "partially approved"


def build_email(
    *,
    booking_code: str,
    actions: list[dict[str, Any]],
    topic: str | None,
) -> dict[str, str]:
    """Craft the subject, html, and text for the user-facing booking confirmation.

    Body stays minimal: outcome, topic, IST date/time, booking code. No
    market context, no per-action breakdown: those belong in admin/audit
    surfaces, not the user inbox.

    Returns a dict with keys: subject, html, text. The html field is sent
    via Resend's `html` field; text is the multipart fallback for clients
    that strip HTML.
    """
    verdict = _verdict(actions)
    slot_human = format_slot_ist(_slot_iso_from_actions(actions))

    subject = f"Booking {booking_code}: {verdict}"

    if verdict == "rejected":
        title = "Booking Rejected"
        rows: list[tuple[str, str]] = [
            ("Topic", topic or "general"),
            ("Requested slot", slot_human),
            ("Booking code", booking_code),
        ]
        body_block = (
            f"Your advisor consultation booking ({booking_code}) has been "
            f"rejected.\n\n"
            "Please book again from the Voice Agent if you'd like another slot."
        )
    else:
        title = (
            "Booking Confirmed"
            if verdict == "approved"
            else "Booking Partially Approved"
        )
        rows = [
            ("Topic", topic or "general"),
            ("Date / time", slot_human),
            ("Booking code", booking_code),
        ]
        body_block = (
            f"Your advisor consultation booking has been {verdict}.\n\n"
            "An advisor will reach out shortly using the contact details on file."
        )

    html_body, text_body = render_card(
        title=title,
        badge=booking_code,
        rows=rows,
        body=body_block,
        footer="Investor Ops",
    )
    return {"subject": subject, "html": html_body, "text": text_body}


def _send_email(*, to: str, subject: str, html: str, text: str) -> dict[str, Any]:
    """Provider call. Resend HTTP API; swap for SendGrid/SES if needed.

    Sends html + text together (Resend accepts both fields and assembles
    a multipart message), so plaintext-only inboxes get the text fallback.
    """
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
        json={
            "from": sender,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": text,
        },
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
        provider_response = _send_email(
            to=to,
            subject=msg["subject"],
            html=msg["html"],
            text=msg["text"],
        )
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
        audit.record_notification(
            _supabase(),
            user_id=user_id,
            call_id=call_id,
            status=status,
            provider_response=provider_response,
        )
    except Exception as exc:
        log.warning("notifications_sent audit insert failed: %s", exc)
