"""Environment-backed settings, loaded via pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    anthropic_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    vapi_api_key: str = ""
    vapi_public_key: str = ""
    vapi_webhook_secret: str = ""
    vapi_assistant_id: str = ""
    frontend_url: str = "http://localhost:3000"
    scrape_shared_secret: str = ""
    corpus_refresh_secret: str = ""
    email_provider: str = ""
    email_api_key: str = ""
    email_from: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_sa_json: str = ""
    google_sa_json_path: str = ""
    google_calendar_id: str = ""
    google_sheets_id: str = ""
    google_sheets_range: str = "Bookings!A:F"
    gmail_mcp_command: str = ""
    gmail_mcp_args: str = ""
    resend_api_key: str = ""


settings = Settings()
