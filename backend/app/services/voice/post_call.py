"""Post-call handler: Vapi webhook → calls row + 3 pending_actions.

Wires Pillar B (voice) into Pillar C (HITL approval queue).

Rules enforced here:
  R-VOICE4: PII-redact transcript and topic before persistence.
  R-VOICE6: generate NL-XXXX booking code on each completed booking.
  R-APPROVE1: every external action lands in pending_actions with status='pending'.
  R-APPROVE2: advisor email payload includes a topic-relevant Market Context
              snippet from the latest weekly pulse (themes + verbatim quote).
              The user-facing confirmation goes through core/notifier.py and
              deliberately omits market context.
"""
from __future__ import annotations

import logging
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client, create_client

from app.config import settings
from app.core.email_template import render_card
from app.core.pii import redact

IST = timezone(timedelta(hours=5, minutes=30))
_WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]
_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_TOPIC_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]+")
# Stop tokens: short / generic words that score noise instead of signal when
# overlapping a topic ("about", "what", "fund") against pulse themes.
_TOPIC_STOPWORDS = {
    "the", "and", "for", "with", "about", "what", "this", "that", "from",
    "into", "your", "have", "has", "are", "was", "were", "will", "would",
    "could", "should", "fund", "funds", "scheme", "schemes",
}

log = logging.getLogger(__name__)

BOOKING_CODE_ALPHABET = string.ascii_uppercase + string.digits
BOOKING_CODE_LEN = 4
BOOKING_CODE_RE = re.compile(r"^NL-[A-Z0-9]{4}$")


def render_advisor_email_body(
    *,
    topic: str,
    slot_human: str,
    booking_code: str,
    market_context: str,
) -> tuple[str, str]:
    """Render the advisor Gmail draft body as (html, text).

    Carries the booking details PLUS a topic-relevant slice of this week's
    pulse so the advisor walks into the call already aware of the wider
    investor sentiment. The user-facing confirmation lives in
    core/notifier.py and intentionally skips market context.
    """
    return render_card(
        title="New Advisor Booking",
        badge=booking_code,
        rows=[
            ("Topic", topic),
            ("Date / time", slot_human),
            ("Booking code", booking_code),
        ],
        body=(
            "Market context (relevant to this booking's topic):\n"
            f"{market_context}\n\n"
            "Please reach out to the user using the contact details on file."
        ),
        footer="Investor Ops",
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


def format_slot_ist(slot_iso: str) -> str:
    """Render a Vapi slot_iso (e.g. '2026-05-05T10:00:00+05:30') for human reading.

    Returns 'Tuesday, May 5 2026 at 10:00 AM IST'. Falls back to the raw string
    plus ' IST' if the value can't be parsed (defensive — Vapi sometimes hands
    back empty/malformed slots).
    """
    if not slot_iso:
        return "to be scheduled"
    try:
        dt = datetime.fromisoformat(slot_iso).astimezone(IST)
    except ValueError:
        return f"{slot_iso} IST"
    weekday = _WEEKDAY_NAMES[dt.weekday()]
    month = _MONTH_NAMES[dt.month]
    hour_24 = dt.hour
    hour_12 = hour_24 % 12 or 12
    suffix = "AM" if hour_24 < 12 else "PM"
    return f"{weekday}, {month} {dt.day} {dt.year} at {hour_12}:{dt.minute:02d} {suffix} IST"


def _load_latest_pulse() -> dict[str, Any] | None:
    """Latest pulses row (themes + quotes + actions). None if no pulse exists."""
    try:
        resp = (
            _supabase()
            .table("pulses")
            .select("themes,quotes")
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        log.warning("pulse lookup for market context failed: %s", exc)
        return None
    rows = resp.data or []
    return rows[0] if rows else None


def _topic_tokens(text: str) -> list[str]:
    """Lowercased ≥3-char tokens, with stopwords stripped."""
    if not text:
        return []
    return [
        tok.lower()
        for tok in _TOPIC_TOKEN_RE.findall(text)
        if len(tok) >= 3 and tok.lower() not in _TOPIC_STOPWORDS
    ]


def _theme_snippet(theme: dict[str, Any], quote: str | None) -> str:
    """Render a single (theme, quote) pair for the advisor email body."""
    name = str(theme.get("name", "")).strip()
    summary = str(theme.get("summary", "")).strip()
    parts: list[str] = []
    if name:
        parts.append(f"Theme: {name}")
        if summary:
            parts[-1] += f" — {summary}"
        else:
            parts[-1] += "."
    elif summary:
        parts.append(summary)
    if quote:
        parts.append(f'Caller verbatim: "{quote.strip()}"')
    return "\n".join(parts) or "no current pulse available"


def _market_context_snippet_for_topic(topic: str) -> str:
    """R-APPROVE2 (refined): topic-aware slice of this week's pulse.

    Picks the theme whose name+summary has the most token overlap with the
    booking topic, and pairs it with the matching verbatim quote (same index)
    when available. Falls back to the joined top-3 theme names when there is
    no pulse, no theme, or the topic shares no meaningful tokens with any
    theme.
    """
    pulse = _load_latest_pulse()
    if not pulse:
        return "no current pulse available"
    themes = pulse.get("themes") or []
    quotes = pulse.get("quotes") or []
    themes = [t for t in themes if isinstance(t, dict)]
    if not themes:
        return "no current pulse available"

    topic_tokens = _topic_tokens(topic)
    if topic_tokens:
        # Weight name matches higher than summary matches so a topic that
        # literally names a theme ("withdrawal failure") beats a summary
        # that incidentally shares one stem ("login... failures dominate").
        best_idx = -1
        best_score = 0
        for i, t in enumerate(themes):
            name_h = str(t.get("name", "")).lower()
            summary_h = str(t.get("summary", "")).lower()
            score = sum(
                3 if tok in name_h else (1 if tok in summary_h else 0)
                for tok in topic_tokens
            )
            if score > best_score:
                best_score = score
                best_idx = i
        if best_idx >= 0:
            quote = quotes[best_idx] if best_idx < len(quotes) else None
            return _theme_snippet(themes[best_idx], quote)

    # Fallback: no overlap or no topic — surface the top 3 theme names so the
    # advisor still gets *some* market context instead of an empty section.
    names = [str(t.get("name", "")).strip() for t in themes]
    names = [n for n in names if n]
    if not names:
        return "no current pulse available"
    return "Top investor themes this week: " + ", ".join(names[:3])


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

    # Vapi Web SDK's vapi.start(id, overrides).metadata lands at
    # call.assistantOverrides.metadata, not call.metadata. Without the third
    # fallback, calls.user_id stays NULL and approve-email later fails with
    # "no recipient email configured for booking user".
    def _from_metadata(key: str) -> str | None:
        return (
            (call.get("metadata") or {}).get(key)
            or (msg.get("metadata") or {}).get(key)
            or ((call.get("assistantOverrides") or {}).get("metadata") or {}).get(key)
        )

    user_id = _from_metadata("user_id")
    metadata_booking_code = _from_metadata("booking_code")
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

    booking_code: str | None = None
    if metadata_booking_code:
        candidate = str(metadata_booking_code).strip().upper()
        if BOOKING_CODE_RE.match(candidate):
            booking_code = candidate
        else:
            log.warning(
                "post-call: ignoring malformed booking_code in metadata: %r",
                metadata_booking_code,
            )

    return {
        "call_id": str(call_id),
        "user_id": str(user_id) if user_id else None,
        "transcript": str(transcript or ""),
        "topic": str(topic or ""),
        "slot_iso": str(slot_iso or ""),
        "intent": intent,
        "booking_code": booking_code,
    }


def _build_pending_actions(
    *,
    call_id: str,
    booking_code: str,
    topic: str,
    slot_iso: str,
    market_context: str,
    user_id: str | None,
    advisor_email: str | None,
) -> list[dict[str, Any]]:
    """The 3 fixed pending actions per booking (R-APPROVE1).

    The email action is the advisor's Gmail draft; recipient is the configured
    advisor inbox (`payload.to`). The user receives a separate notification via
    core/notifier.py once all three actions hit a terminal state.
    """
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
    html_body, text_body = render_advisor_email_body(
        topic=topic or "general",
        slot_human=format_slot_ist(slot_iso),
        booking_code=booking_code,
        market_context=market_context,
    )
    email_payload = {
        "subject": f"New advisor booking {booking_code}: {topic or 'general'}",
        "body": html_body,
        "text": text_body,
        "mime_type": "text/html",
        "market_context": market_context,
        "booking_code": booking_code,
        "to": advisor_email or None,
        "audience": "advisor",
    }
    return [
        {"call_id": call_id, "type": "calendar", "payload": calendar_payload, "status": "pending"},
        {"call_id": call_id, "type": "sheets", "payload": sheets_payload, "status": "pending"},
        {"call_id": call_id, "type": "email", "payload": email_payload, "status": "pending"},
    ]


def _parse_slot_iso(slot_iso: str) -> datetime | None:
    """Best-effort parse of a Vapi slot string. Returns None for empty/garbage."""
    if not slot_iso:
        return None
    try:
        return datetime.fromisoformat(slot_iso)
    except (TypeError, ValueError):
        return None


def _is_actionable_booking(*, intent: str, topic: str, slot_iso: str) -> bool:
    """Did this call actually capture a booking we can act on?

    All three must hold:
      - intent is book_new or reschedule (cancel never queues new actions)
      - topic is non-empty after PII redaction
      - slot_iso parses as ISO-8601 datetime (Vapi sometimes hands back "" or
        a malformed marker when the analysis couldn't extract a slot)

    Calls that fail this gate persist to `calls` with status='abandoned' for
    audit but do NOT queue calendar/sheets/email actions for admin approval.
    """
    if intent not in ("book_new", "reschedule"):
        return False
    if not (topic or "").strip():
        return False
    if _parse_slot_iso(slot_iso) is None:
        return False
    return True


def _existing_call(call_id: str) -> dict[str, Any] | None:
    """Return the persisted call row if one already exists, else None.

    Used to make handle_post_call idempotent: if Vapi delivers the same
    end-of-call-report twice, we reuse the original booking_code and skip
    the pending_actions insert.
    """
    resp = (
        _supabase()
        .table("calls")
        .select("id,booking_code,status")
        .eq("id", call_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def handle_post_call(raw_payload: dict[str, Any]) -> dict[str, Any]:
    """Synchronous handler invoked from the FastAPI route via asyncio.to_thread.

    Idempotent on call_id: a second delivery of the same end-of-call-report
    refreshes transcript/topic on the calls row but does not insert duplicate
    pending_actions.

    Steps:
      1. Extract & validate payload
      2. Look up the call; reuse booking_code if it already exists
      3. PII-guard transcript + topic
      4. Decide actionability: a real booking needs intent=book_new/reschedule,
         a non-empty topic, and a parseable slot_iso. If any are missing the
         call is recorded with status='abandoned' and NO pending_actions are
         queued (the admin shouldn't approve a calendar hold for a call that
         never actually agreed on a slot).
      5. Upsert calls row.
      6. Insert 3 pending_actions ONLY on first delivery AND only when the
         booking is actionable.
      7. Return summary for the webhook response.
    """
    parsed = _extract_payload(raw_payload)

    safe_transcript = redact(parsed["transcript"])
    safe_topic = redact(parsed["topic"]).strip()
    safe_slot = parsed["slot_iso"]

    existing = _existing_call(parsed["call_id"])
    is_redelivery = bool(existing)
    # Priority: existing row (idempotency) → metadata code minted at call start
    # (so the agent and the persisted record agree) → fresh fallback.
    booking_code = (
        (existing or {}).get("booking_code")
        or parsed.get("booking_code")
        or generate_booking_code()
    )
    market_context = _market_context_snippet_for_topic(safe_topic)
    advisor_email = (settings.advisor_email or "").strip() or None

    actionable = _is_actionable_booking(
        intent=parsed["intent"], topic=safe_topic, slot_iso=safe_slot
    )

    now = datetime.now(timezone.utc).isoformat()
    call_row = {
        "id": parsed["call_id"],
        "user_id": parsed["user_id"],
        "intent": parsed["intent"],
        "topic": safe_topic or None,
        "transcript": safe_transcript or None,
        "booking_code": booking_code,
        "status": "completed" if actionable else "abandoned",
        "ended_at": now,
    }
    _supabase().table("calls").upsert(call_row, on_conflict="id").execute()

    if is_redelivery:
        log.info(
            "post-call: redelivery for call=%s; skipping pending_actions insert",
            parsed["call_id"],
        )
        return {
            "call_id": parsed["call_id"],
            "booking_code": booking_code,
            "pending_actions": 0,
            "booking_captured": actionable,
            "market_context": market_context,
            "redelivery": True,
        }

    if not actionable:
        log.info(
            "post-call: call=%s ended without a confirmed booking "
            "(intent=%s topic_present=%s slot_present=%s); status=abandoned, "
            "no pending_actions queued",
            parsed["call_id"],
            parsed["intent"],
            bool(safe_topic),
            bool(_parse_slot_iso(safe_slot)),
        )
        return {
            "call_id": parsed["call_id"],
            "booking_code": booking_code,
            "pending_actions": 0,
            "booking_captured": False,
            "market_context": market_context,
        }

    actions = _build_pending_actions(
        call_id=parsed["call_id"],
        booking_code=booking_code,
        topic=safe_topic,
        slot_iso=safe_slot,
        market_context=market_context,
        user_id=parsed["user_id"],
        advisor_email=advisor_email,
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
        "booking_captured": True,
        "pending_actions": len(actions),
        "market_context": market_context,
    }
