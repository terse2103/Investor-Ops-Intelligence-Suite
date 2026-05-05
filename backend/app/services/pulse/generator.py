"""Pulse generator for Weekly Product Pulse (services/pulse/generator.py).

R-PULSE1: max 5 clustered themes.
R-PULSE2: top 3 themes surfaced, written to current_themes.
R-PULSE3: exactly 3 verbatim user quotes.
R-PULSE4: ≤250-word pulse note.
R-PULSE5: exactly 3 action ideas.
R-PULSE6: PII guard on quotes and themes.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone

from supabase import Client, create_client

from app.config import settings
from app.core.llm import complete_text
from app.core.pii import redact

log = logging.getLogger(__name__)

PULSE_WINDOW_WEEKS = 10  # matches scraper R-SCRAPE3 window
MAX_REVIEWS_FOR_PULSE = 200
# 4x the default RAG budget: pulse JSON is ~1.5K tokens and adaptive thinking
# burns several K more on review clustering. 2K leaves zero room for text.
PULSE_MAX_TOKENS = 16384

PULSE_SYSTEM_PROMPT = """\
You are the Investor Ops & Intelligence Suite Pulse Generator.
Your job: analyse the provided INDMoney Play Store review texts and produce a structured weekly pulse.

Rules (strict):
1. Cluster reviews into AT MOST 5 themes.
2. Pick the TOP 3 themes by review count.
3. Select EXACTLY 3 verbatim quotes from real reviews (one per top theme if possible).
4. Write a pulse note of AT MOST 250 words covering the top 3 themes and their trends.
5. List EXACTLY 3 product action ideas. Each action MUST be a single concise, imperative bullet (≤15 words), not a paragraph. Start with a verb (e.g. "Add", "Fix", "Surface", "Reduce"). No multi-sentence rationale.
6. Keep each theme "summary" to ONE short sentence (≤20 words). The combined themes (name + summary) + quotes + actions text shown to admins MUST be ≤ 250 words total. Trim summaries and actions before exceeding this cap; this is a hard limit, not a target.
7. Output JSON only, matching this schema exactly:
   {
     "themes": [
       {"name": "Theme Name", "review_count": N, "summary": "one sentence ≤20 words"},
       {"name": "Theme Name", "review_count": N, "summary": "one sentence ≤20 words"},
       {"name": "Theme Name", "review_count": N, "summary": "one sentence ≤20 words"}
     ],
     "quotes": ["verbatim quote 1", "verbatim quote 2", "verbatim quote 3"],
     "pulse_note": "≤250-word text",
     "actions": ["short imperative bullet 1", "short imperative bullet 2", "short imperative bullet 3"]
   }

Do not include any text outside the JSON block.\
"""

RETRY_REMINDER = (
    "\n\nYour previous response violated these rules: {violations}. "
    "Regenerate the JSON, this time matching the schema and constraints exactly."
)

_client: Client | None = None


def _supabase() -> Client:
    """Lazy singleton Supabase client (service-role)."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def _visible_word_count(pulse: dict) -> int:
    """Words across the admin-visible content: theme names + summaries + quotes + actions.

    Mirrors what the Weekly Pulse page actually renders (the pulse_note is
    hidden from the UI but checked separately by R-PULSE4). Numeric fields
    like review_count are excluded; they're chrome, not prose.
    """
    chunks: list[str] = []

    for t in pulse.get("themes") or []:
        if not isinstance(t, dict):
            continue
        name = str(t.get("name", "")).strip()
        summary = str(t.get("summary", "")).strip()
        if name:
            chunks.append(name)
        if summary:
            chunks.append(summary)

    for q in pulse.get("quotes") or []:
        if isinstance(q, str) and q.strip():
            chunks.append(q.strip())

    for a in pulse.get("actions") or []:
        if isinstance(a, str) and a.strip():
            chunks.append(a.strip())

    return sum(len(c.split()) for c in chunks)


def _validate_pulse(pulse: dict) -> list[str]:
    """Return a list of rule violations in the generated pulse. Empty = valid."""
    errors: list[str] = []
    themes = pulse.get("themes")
    quotes = pulse.get("quotes")
    actions = pulse.get("actions")
    pulse_note = pulse.get("pulse_note", "")

    if not isinstance(themes, list) or len(themes) != 3:
        errors.append(
            f"R-PULSE2: expected 3 themes, got {0 if not isinstance(themes, list) else len(themes)}"
        )
    else:
        for i, t in enumerate(themes):
            if not isinstance(t, dict) or "name" not in t or "review_count" not in t:
                errors.append(f"R-PULSE2: theme[{i}] missing required keys (name, review_count)")
                break

    if not isinstance(quotes, list) or len(quotes) != 3:
        errors.append(
            f"R-PULSE3: expected 3 quotes, got {0 if not isinstance(quotes, list) else len(quotes)}"
        )

    if not isinstance(actions, list) or len(actions) != 3:
        errors.append(
            f"R-PULSE5: expected 3 actions, got {0 if not isinstance(actions, list) else len(actions)}"
        )

    if not isinstance(pulse_note, str) or len(pulse_note.split()) > 250:
        word_count = len(pulse_note.split()) if isinstance(pulse_note, str) else 0
        errors.append(f"R-PULSE4: pulse note is {word_count} words (max 250)")

    visible_words = _visible_word_count(pulse)
    if visible_words > 250:
        errors.append(
            f"R-PULSE7: themes+quotes+actions combined is {visible_words} words (max 250); "
            "tighten theme summaries and action bullets"
        )

    return errors


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _parse_json_response(raw: str) -> dict:
    """Strip optional markdown fences, parse JSON. Raises ValueError on failure."""
    if not raw:
        raise ValueError("empty LLM response")
    cleaned = _FENCE_RE.sub("", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"could not parse JSON from LLM response: {exc}") from exc


def _format_review_block(reviews: list[dict]) -> str:
    """Render reviews into a numbered prompt block."""
    lines = ["INDMoney Play Store reviews (last 8-10 weeks):", ""]
    for i, r in enumerate(reviews, start=1):
        rating = r.get("rating", "?")
        content = (r.get("content") or "").strip()
        lines.append(f"[{i}] (rating={rating}) {content}")
    return "\n".join(lines)


def _redact_pulse(pulse: dict) -> dict:
    """R-PULSE6: PII-redact every quote and theme name."""
    quotes = pulse.get("quotes") or []
    pulse["quotes"] = [redact(q) for q in quotes]

    themes = pulse.get("themes") or []
    redacted_themes = []
    for t in themes:
        if isinstance(t, dict):
            t = {**t, "name": redact(t.get("name", "")), "summary": redact(t.get("summary", ""))}
        redacted_themes.append(t)
    pulse["themes"] = redacted_themes

    if isinstance(pulse.get("pulse_note"), str):
        pulse["pulse_note"] = redact(pulse["pulse_note"])
    return pulse


def _load_recent_reviews() -> list[dict]:
    """Pull reviews posted within the last PULSE_WINDOW_WEEKS, newest first."""
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=PULSE_WINDOW_WEEKS)).isoformat()
    resp = (
        _supabase()
        .table("reviews")
        .select("play_review_id,content,rating,posted_at")
        .gte("posted_at", cutoff)
        .order("posted_at", desc=True)
        .limit(MAX_REVIEWS_FOR_PULSE)
        .execute()
    )
    return resp.data or []


async def generate_pulse() -> dict:
    """Generate a pulse from recent reviews and persist it.

    Returns:
        The validated, PII-redacted pulse dict that was written to the DB.

    Raises:
        ValueError if validation still fails after one retry, or if there are
        no reviews in the window.
    """
    reviews = await asyncio.to_thread(_load_recent_reviews)
    if not reviews:
        raise ValueError("no reviews in window; cannot generate pulse")

    log.info("Generating pulse from %d reviews", len(reviews))
    user_content = _format_review_block(reviews)

    pulse, violations = await asyncio.to_thread(
        _generate_and_validate, PULSE_SYSTEM_PROMPT, user_content
    )

    if violations:
        log.warning("Pulse validation failed: %s; retrying once", violations)
        retry_system = PULSE_SYSTEM_PROMPT + RETRY_REMINDER.format(violations="; ".join(violations))
        pulse, violations = await asyncio.to_thread(
            _generate_and_validate, retry_system, user_content
        )
        if violations:
            raise ValueError(f"pulse generation failed validation twice: {violations}")

    pulse = _redact_pulse(pulse)

    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(weeks=PULSE_WINDOW_WEEKS)
    pulse_id = await asyncio.to_thread(_persist_pulse, pulse, window_start, window_end)
    await asyncio.to_thread(_upsert_current_themes, pulse_id, pulse["themes"])

    log.info("Pulse %s persisted; current_themes updated", pulse_id)
    return pulse


def _generate_and_validate(system_prompt: str, user_content: str) -> tuple[dict, list[str]]:
    """Call the LLM and validate. Returns (pulse, violations). Sync; wrap in to_thread."""
    raw = complete_text(
        system_prompt=system_prompt,
        user_content=user_content,
        max_tokens=PULSE_MAX_TOKENS,
    )
    try:
        pulse = _parse_json_response(raw)
    except ValueError as exc:
        return {}, [f"R-PULSE-PARSE: {exc}"]
    return pulse, _validate_pulse(pulse)


def _persist_pulse(
    pulse: dict, window_start: datetime, window_end: datetime
) -> str:
    """Insert into pulses table; return the new row id."""
    note_text = pulse.get("pulse_note", "")
    word_count = len(note_text.split())
    row = {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "themes": pulse.get("themes", []),
        "quotes": pulse.get("quotes", []),
        "actions": pulse.get("actions", []),
        "note_text": note_text,
        "word_count": word_count,
    }
    resp = _supabase().table("pulses").insert(row).execute()
    if not resp.data:
        raise RuntimeError("pulses insert returned no rows")
    return resp.data[0]["id"]


def _upsert_current_themes(pulse_id: str, themes: list[dict]) -> None:
    """Refresh the singleton current_themes row (id=1) for Vapi injection."""
    payload = {
        "id": 1,
        "pulse_id": pulse_id,
        "themes": themes,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _supabase().table("current_themes").upsert(payload, on_conflict="id").execute()


def load_latest_pulse() -> dict | None:
    """Return the most recent pulse row (or None if no pulses exist)."""
    resp = (
        _supabase()
        .table("pulses")
        .select("*")
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        return None
    return resp.data[0]
