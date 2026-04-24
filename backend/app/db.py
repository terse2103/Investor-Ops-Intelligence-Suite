"""Supabase client using the service-role key. Backend-only; bypasses RLS."""
from supabase import Client, create_client

from app.config import settings


def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
