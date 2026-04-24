"""User settings: notification email (used by the notifier on booking decisions)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from app.core.auth import require_auth

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ContactIn(BaseModel):
    email: EmailStr


@router.post("/contact")
async def update_contact(
    payload: ContactIn,
    user: dict = Depends(require_auth),
) -> dict:
    """Upsert the caller's notification email in user_contacts.

    TODO (Day 5): upsert via Supabase service-role client using user["id"].
    """
    return {"status": "not_implemented", "email": payload.email}
