"""FastAPI auth dependencies backed by Supabase JWT validation."""
from __future__ import annotations

import asyncio
import logging

from fastapi import Depends, Header, HTTPException, status
from supabase import Client, create_client

from app.config import settings

log = logging.getLogger(__name__)

_client: Client | None = None


def _supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


async def require_auth(authorization: str | None = Header(default=None)) -> dict:
    """Validate the Supabase JWT and return the caller's user dict."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        resp = await asyncio.to_thread(_supabase().auth.get_user, token)
    except Exception as exc:
        log.warning("Supabase get_user error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
        ) from exc
    if resp.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return {
        "id": str(resp.user.id),
        "email": resp.user.email,
        "role": (resp.user.app_metadata or {}).get("role", "user"),
    }


async def require_admin(user: dict = Depends(require_auth)) -> dict:
    """Extend require_auth to also enforce admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
