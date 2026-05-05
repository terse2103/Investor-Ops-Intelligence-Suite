"""Audit-row writers for scrape_runs, action_audit, and notifications_sent.

Each function takes a Supabase client (callers reuse their existing
service-role connection, and tests can patch one ``_supabase`` per call site).
Row shapes match the columns in ``supabase/migrations/0001_init.sql``.

Tables:
  scrape_runs        - one row per /api/scrape invocation (success or error).
  action_audit       - one row per executed pending_action (R-APPROVE3).
  notifications_sent - one row per booking-decision notification attempt.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_scrape_run(
    client: Client,
    *,
    started_at: str,
    status: str,
    trigger_source: str | None,
    review_count: int = 0,
    filtered_out_count: int = 0,
    finished_at: str | None = None,
    error_message: str | None = None,
) -> None:
    """Insert a row into scrape_runs. ``status`` must be one of
    'running' | 'ok' | 'rate_limited' | 'error'."""
    client.table("scrape_runs").insert(
        {
            "started_at": started_at,
            "finished_at": finished_at or _now_iso(),
            "status": status,
            "review_count": review_count,
            "filtered_out_count": filtered_out_count,
            "trigger_source": trigger_source,
            "error_message": error_message,
        }
    ).execute()


def record_action(
    client: Client,
    *,
    pending_action_id: str,
    status: str,
    provider_response: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    """Insert a row into action_audit. ``status`` is 'ok' | 'failed'."""
    client.table("action_audit").insert(
        {
            "pending_action_id": pending_action_id,
            "status": status,
            "provider_response": provider_response,
            "error_message": error_message,
        }
    ).execute()


def record_notification(
    client: Client,
    *,
    user_id: str | None,
    call_id: str,
    status: str,
    provider_response: dict[str, Any] | None = None,
) -> None:
    """Insert a row into notifications_sent. ``status`` is one of
    'sent' | 'bounced' | 'provider_error' | 'skipped_no_contact'."""
    client.table("notifications_sent").insert(
        {
            "user_id": user_id,
            "call_id": call_id,
            "status": status,
            "provider_response": provider_response,
        }
    ).execute()
