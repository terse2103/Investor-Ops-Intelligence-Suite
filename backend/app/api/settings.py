"""User settings: notification email (used by the notifier on booking decisions)."""
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ContactIn(BaseModel):
    email: EmailStr


@router.post("/contact")
async def update_contact(payload: ContactIn) -> dict:
    """Upsert the caller's notification email in user_contacts.

    TODO (Day 5): auth check; upsert via Supabase service-role client.
    """
    return {"status": "not_implemented", "email": payload.email}
