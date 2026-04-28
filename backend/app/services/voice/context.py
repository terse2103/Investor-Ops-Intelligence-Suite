"""Voice context: read current_themes singleton for Vapi dynamic-variable injection.

Pillar B end-to-end glue: scraper -> pulse -> current_themes -> /api/voice/context
-> Vapi dynamic variables -> theme-aware greeting (R-VOICE2).
"""
from __future__ import annotations

import logging

from supabase import Client, create_client

from app.config import settings

log = logging.getLogger(__name__)

_client: Client | None = None


def _supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


def _theme_name(theme: object) -> str:
    """Pull a string name from a theme entry (dict from pulse generator, str fallback)."""
    if isinstance(theme, dict):
        return str(theme.get("name", "")).strip()
    return str(theme).strip()


def load_current_themes() -> list[str]:
    """Return up to 3 theme name strings from the current_themes singleton.

    Empty list if the row exists but has no themes, or if no pulse has been
    generated yet. Never raises in the singleton-missing case so the voice
    endpoint can degrade gracefully (R-VOICE2 still callable with no themes).
    """
    try:
        resp = (
            _supabase()
            .table("current_themes")
            .select("themes,updated_at")
            .eq("id", 1)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # network / auth failure
        log.warning("Failed to load current_themes: %s", exc)
        return []

    rows = resp.data or []
    if not rows:
        return []
    raw = rows[0].get("themes") or []
    names = [n for n in (_theme_name(t) for t in raw) if n]
    return names[:3]


def to_vapi_variables(themes: list[str]) -> dict:
    """Format themes as a flat dict Vapi can interpolate into the system prompt.

    Keys top_theme_1/2/3 are referenced as {{top_theme_1}} etc. in the Vapi
    assistant prompt. Unfilled slots default to empty string so the prompt
    template never renders a literal `{{top_theme_2}}` to the caller.
    """
    return {
        "top_theme_1": themes[0] if len(themes) >= 1 else "",
        "top_theme_2": themes[1] if len(themes) >= 2 else "",
        "top_theme_3": themes[2] if len(themes) >= 3 else "",
        "themes_joined": ", ".join(themes) if themes else "",
        "themes_count": str(len(themes)),
    }
