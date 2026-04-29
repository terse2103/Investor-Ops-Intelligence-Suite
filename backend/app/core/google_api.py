"""Google Calendar + Sheets clients used by the approval dispatcher.

Both APIs use a service-account credential. The SA JSON can be supplied either:
  - inline via `GOOGLE_SA_JSON` (preferred on Render: no filesystem persistence)
  - on disk via `GOOGLE_SA_JSON_PATH` (preferred for local dev)

Calendar: `create_tentative_event` writes to `GOOGLE_CALENDAR_ID` with status
"tentative". The calendar must be shared with the SA email (read+write).

Sheets: `append_booking_row` appends to `GOOGLE_SHEETS_ID` at
`GOOGLE_SHEETS_RANGE`. The spreadsheet must be shared with the SA email (Editor).

All callers in tests should patch `_calendar_service` / `_sheets_service`
rather than building a real credential.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build

from app.config import settings

log = logging.getLogger(__name__)

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def _load_sa_credentials(scopes: list[str]) -> Credentials:
    """Build SA credentials from inline JSON or a filesystem path."""
    if settings.google_sa_json:
        info = json.loads(settings.google_sa_json)
        return Credentials.from_service_account_info(info, scopes=scopes)
    if settings.google_sa_json_path:
        return Credentials.from_service_account_file(
            settings.google_sa_json_path, scopes=scopes
        )
    raise RuntimeError(
        "GOOGLE_SA_JSON or GOOGLE_SA_JSON_PATH must be set for Google API access"
    )


@lru_cache(maxsize=1)
def _calendar_service() -> Resource:
    creds = _load_sa_credentials([CALENDAR_SCOPE])
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


@lru_cache(maxsize=1)
def _sheets_service() -> Resource:
    creds = _load_sa_credentials([SHEETS_SCOPE])
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def create_tentative_event(*, payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a tentative-status event into the configured calendar.

    payload keys (from voice/post_call._build_pending_actions):
      - summary, description, start_iso, duration_minutes, timezone

    Returns the Google API response (event resource). Raises on misconfiguration
    or upstream errors; the caller writes the audit row.
    """
    calendar_id = settings.google_calendar_id
    if not calendar_id:
        raise RuntimeError("GOOGLE_CALENDAR_ID not configured")

    start_iso = payload["start_iso"]
    duration_min = int(payload.get("duration_minutes", 30))
    tz = payload.get("timezone", "Asia/Kolkata")

    event = {
        "summary": payload.get("summary", "Advisor consultation"),
        "description": payload.get("description", ""),
        "start": {"dateTime": start_iso, "timeZone": tz},
        "end": _compute_end(start_iso, duration_min, tz),
        "status": "tentative",
    }
    log.info("calendar.create_tentative_event start=%s tz=%s", start_iso, tz)
    return (
        _calendar_service()
        .events()
        .insert(calendarId=calendar_id, body=event)
        .execute()
    )


def _compute_end(start_iso: str, duration_min: int, tz: str) -> dict[str, str]:
    """Compute the event end as ISO 8601 in the same timezone."""
    from datetime import datetime, timedelta

    start_dt = datetime.fromisoformat(start_iso)
    end_dt = start_dt + timedelta(minutes=duration_min)
    return {"dateTime": end_dt.isoformat(), "timeZone": tz}


def append_booking_row(*, payload: dict[str, Any]) -> dict[str, Any]:
    """Append one row to the Advisor Pre-Bookings sheet.

    payload keys: booking_code, user_id, topic, slot_iso, created_at.

    Returns the Sheets API response (updates resource).
    """
    sheets_id = settings.google_sheets_id
    if not sheets_id:
        raise RuntimeError("GOOGLE_SHEETS_ID not configured")

    row = [
        payload.get("created_at", ""),
        payload.get("booking_code", ""),
        payload.get("user_id", ""),
        payload.get("topic", ""),
        payload.get("slot_iso", ""),
        "pending",
    ]
    log.info("sheets.append_booking_row code=%s topic=%s", row[1], row[3])
    return (
        _sheets_service()
        .spreadsheets()
        .values()
        .append(
            spreadsheetId=sheets_id,
            range=settings.google_sheets_range,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        )
        .execute()
    )
