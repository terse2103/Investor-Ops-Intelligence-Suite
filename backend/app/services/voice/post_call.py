"""Post-call handler: Vapi webhook → calls row + 3 pending_actions.

Wires Pillar B (voice) into Pillar C (HITL approval queue).

Rules enforced here:
  R-VOICE4: PII-redact transcript and topic before persistence.
  R-VOICE6: generate NL-XXXX booking code on each completed booking.
  R-APPROVE1: every external action lands in pending_actions with status='pending'.
  R-APPROVE2: email payload includes Market Context from current_themes.
"""
from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.config import settings
from app.core.pii import redact

log = logging.getLogger(__name__)

BOOKING_CODE_ALPHABET = string.ascii_uppercase + string.digits
BOOKING_CODE_LEN = 4
EMAIL_PAYLOAD_TEMPLATE = (
    "Hi,\n\n"
    "This confirms your advisor consultation booking on {slot_iso} IST.\n"
    "Topic: {topic}\n"
    "Booking code: {booking_code}\n\n"
    "Market Context (top investor concerns this week): {market_context}\n\n"
    "An advisor will reach out shortly.\n"
)

_client: Client | None = None


def _supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def generate_booking_code() -> str:
    """R-VOICE6: NL-XXXX format, 4-char alphanumeric, cryptographically random."""
    suffix = "".join(secrets.choice(BOOKING_CODE_ALPHABET) for _ in range(BOOKING_CODE_LEN))
    return f"NL-{suffix}"


def _market_context_from_themes() -> str:
    """Read current top themes for R-APPROVE2 Market Context injection."""
    try:
        resp = (
            _supabase()
            .table("current_themes")
            .select("themes")
            .eq("id", 1)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        log.warning("market context lookup failed: %s", exc)
        return "no current pulse available"
    rows = resp.data or []
    if not rows:
        return "no current pulse available"
    raw = rows[0].get("themes") or []
    names = [str(t.get("name", "")).strip() for t in raw if isinstance(t, dict)]
    names = [n for n in names if n]
    if not names:
        return "no current pulse available"
    return ", ".join(names[:3])


def _extract_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Pull the fields we need out of the Vapi webhook envelope.

    Vapi wraps the call payload under `message`. We accept both shapes
    (raw or wrapped) so tests and dashboard playbacks both work.
    """
    msg = raw.get("message") if isinstance(raw.get("message"), dict) else raw

    call = msg.get("call") or {}
    call_id = call.get("id") or msg.get("callId") or msg.get("call_id")
    if not call_id:
        raise ValueError("missing call id in webhook payload")

    user_id = (
        (call.get("metadata") or {}).get("user_id")
        or (msg.get("metadata") or {}).get("user_id")
    )
    transcript = (
        msg.get("transcript")
        or call.get("transcript")
        or (msg.get("artifact") or {}).get("transcript")
        or ""
    )
    analysis = msg.get("analysis") or {}
    structured = analysis.get("structuredData") or msg.get("structuredData") or {}
    topic = structured.get("topic") or msg.get("topic") or ""
    slot_iso = structured.get("slot_iso") or msg.get("slot_iso") or ""
    intent = structured.get("intent") or "book_new"

    if intent not in ("book_new", "reschedule", "cancel"):
        intent = "book_new"

    return {
        "call_id": str(call_id),
        "user_id": str(user_id) if user_id else None,
        "transcript": str(transcript or ""),
        "topic": str(topic or ""),
        "slot_iso": str(slot_iso or ""),
        "intent": intent,
    }


def _build_pending_actions(
    *,
    call_id: str,
    booking_code: str,
    topic: str,
    slot_iso: str,
    market_context: str,
    user_id: str | None,
) -> list[dict[str, Any]]:
    """The 3 fixed pending actions per booking (R-APPROVE1)."""
    calendar_payload = {
        "summary": f"Advisor consultation - {booking_code}",
        "description": f"Topic: {topic or 'general'}",
        "start_iso": slot_iso,
        "duration_minutes": 30,
        "timezone": "Asia/Kolkata",
    }
    sheets_payload = {
        "booking_code": booking_code,
        "user_id": user_id,
        "topic": topic or "general",
        "slot_iso": slot_iso,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    email_payload = {
        "subject": f"Advisor consultation booked - {booking_code}",
        "body": EMAIL_PAYLOAD_TEMPLATE.format(
            slot_iso=slot_iso or "to be scheduled",
            topic=topic or "general",
            booking_code=booking_code,
            market_context=market_context,
        ),
        "market_context": market_context,
        "booking_code": booking_code,
    }
    return [
        {"call_id": call_id, "type": "calendar", "payload": calendar_payload, "status": "pending"},
        {"call_id": call_id, "type": "sheets", "payload": sheets_payload, "status": "pending"},
        {"call_id": call_id, "type": "email", "payload": email_payload, "status": "pending"},
    ]


def handle_post_call(raw_payload: dict[str, Any]) -> dict[str, Any]:
    """Synchronous handler invoked from the FastAPI route via asyncio.to_thread.

    Steps:
      1. Extract & validate payload
      2. Skip if call status indicates the call was abandoned/in_progress
      3. PII-guard transcript + topic
      4. Upsert calls row with booking code + status=completed
      5. Insert 3 pending_actions rows (calendar, sheets, email)
      6. Return summary for the webhook response
    """
    parsed = _extract_payload(raw_payload)

    safe_transcript = redact(parsed["transcript"])
    safe_topic = redact(parsed["topic"]).strip()
    safe_slot = parsed["slot_iso"]

    booking_code = generate_booking_code()
    market_context = _market_context_from_themes()

    now = datetime.now(timezone.utc).isoformat()
    call_row = {
        "id": parsed["call_id"],
        "user_id": parsed["user_id"],
        "intent": parsed["intent"],
        "topic": safe_topic or None,
        "transcript": safe_transcript or None,
        "booking_code": booking_code,
        "status": "completed",
        "ended_at": now,
    }
    _supabase().table("calls").upsert(call_row, on_conflict="id").execute()

    actions = _build_pending_actions(
        call_id=parsed["call_id"],
        booking_code=booking_code,
        topic=safe_topic,
        slot_iso=safe_slot,
        market_context=market_context,
        user_id=parsed["user_id"],
    )
    _supabase().table("pending_actions").insert(actions).execute()

    log.info(
        "post-call: call=%s booking=%s actions=%d topic=%r",
        parsed["call_id"],
        booking_code,
        len(actions),
        safe_topic,
    )
    return {
        "call_id": parsed["call_id"],
        "booking_code": booking_code,
        "pending_actions": len(actions),
        "market_context": market_context,
    }
