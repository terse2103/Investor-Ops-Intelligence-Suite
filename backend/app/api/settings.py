"""User settings: notification email (used by the notifier on booking decisions)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from supabase import Client, create_client

from app.config import settings as app_settings
from app.core.auth import require_auth

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

_client: Client | None = None


def _supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            app_settings.supabase_url, app_settings.supabase_service_role_key
        )
    return _client


class ContactIn(BaseModel):
    email: EmailStr


class ContactOut(BaseModel):
    email: str | None = None
    updated_at: str | None = None


def _read_contact(user_id: str) -> dict | None:
    resp = (
        _supabase()
        .table("user_contacts")
        .select("email,updated_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None


def _upsert_contact(user_id: str, email: str) -> dict:
    payload = {
        "user_id": user_id,
        "email": email,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = (
        _supabase()
        .table("user_contacts")
        .upsert(payload, on_conflict="user_id")
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else payload


@router.get("/contact", response_model=ContactOut)
async def get_contact(user: dict = Depends(require_auth)) -> ContactOut:
    row = await asyncio.to_thread(_read_contact, user["id"])
    if not row:
        return ContactOut()
    return ContactOut(email=row.get("email"), updated_at=row.get("updated_at"))


@router.post("/contact", response_model=ContactOut)
async def update_contact(
    payload: ContactIn,
    user: dict = Depends(require_auth),
) -> ContactOut:
    """Upsert the caller's notification email in user_contacts."""
    try:
        row = await asyncio.to_thread(_upsert_contact, user["id"], str(payload.email))
    except Exception as exc:
        log.exception("contact upsert failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to save contact: {exc}",
        ) from exc
    return ContactOut(email=row.get("email"), updated_at=row.get("updated_at"))
