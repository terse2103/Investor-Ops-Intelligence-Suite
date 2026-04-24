"""Pulse generator for Weekly Product Pulse (services/pulse/generator.py).

R-PULSE1: max 5 clustered themes.
R-PULSE2: top 3 themes surfaced, written to current_themes.
R-PULSE3: exactly 3 verbatim user quotes.
R-PULSE4: ≤250-word pulse note.
R-PULSE5: exactly 3 action ideas.
R-PULSE6: PII guard on quotes and themes.
"""
from __future__ import annotations

import logging

from app.core.llm import answer_from_context
from app.core.pii import redact

log = logging.getLogger(__name__)

# Pulse generation prompt (baked-in rules: max 5 themes, top 3, 3 quotes, ≤250 words, 3 actions).
# Full prompt template resolved on Day 3.
PULSE_SYSTEM_PROMPT = """\
You are the Investor Ops & Intelligence Suite Pulse Generator.
Your job: analyse the provided INDMoney Play Store review texts and produce a structured weekly pulse.

Rules (strict):
1. Cluster reviews into AT MOST 5 themes.
2. Pick the TOP 3 themes by review count.
3. Select EXACTLY 3 verbatim quotes from real reviews (one per top theme if possible).
4. Write a pulse note of AT MOST 250 words covering the top 3 themes and their trends.
5. List EXACTLY 3 product action ideas (concrete, product-team-facing).
6. Output JSON only, matching this schema exactly:
   {
     "themes": [
       {"name": "Theme Name", "review_count": N, "summary": "one sentence"},
       ... (top 3 only)
     ],
     "quotes": ["verbatim quote 1", "verbatim quote 2", "verbatim quote 3"],
     "pulse_note": "≤250-word text",
     "actions": ["action 1", "action 2", "action 3"]
   }

Do not include any text outside the JSON block.\
"""


def _validate_pulse(pulse: dict) -> list[str]:
    """Return a list of rule violations in the generated pulse. Empty = valid."""
    errors: list[str] = []
    themes = pulse.get("themes", [])
    quotes = pulse.get("quotes", [])
    actions = pulse.get("actions", [])
    pulse_note = pulse.get("pulse_note", "")

    if len(themes) > 3:
        errors.append(f"R-PULSE2: expected 3 themes, got {len(themes)}")
    if len(quotes) != 3:
        errors.append(f"R-PULSE3: expected 3 quotes, got {len(quotes)}")
    if len(actions) != 3:
        errors.append(f"R-PULSE5: expected 3 actions, got {len(actions)}")
    word_count = len(pulse_note.split())
    if word_count > 250:
        errors.append(f"R-PULSE4: pulse note is {word_count} words (max 250)")

    return errors


async def generate_pulse(review_texts: list[str]) -> dict:
    """Generate a pulse from the provided review texts.

    Args:
        review_texts: List of English review texts (already filtered + PII-guarded).

    Returns:
        Validated pulse dict with keys: themes, quotes, pulse_note, actions.

    TODO (Day 3):
    1. Load recent reviews from Supabase (R-SCRAPE3 window already applied at ingest)
    2. Call answer_from_context() with PULSE_SYSTEM_PROMPT
    3. Parse the JSON response
    4. Validate with _validate_pulse(); retry once with stricter prompt if violations
    5. PII-guard quotes and theme names (R-PULSE6)
    6. Write pulse row to `pulses` table
    7. Upsert current_themes singleton row
    """
    raise NotImplementedError("generate_pulse is implemented on Day 3")
