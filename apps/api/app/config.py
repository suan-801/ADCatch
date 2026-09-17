from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:password@localhost:5432/adcatch"

    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_storage_bucket: str = "ad-thumbnails"

    apify_token: str = ""
    apify_actor: str = "curious_coder/facebook-ads-library-scraper"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    teams_webhook_url: str = ""

    default_admin_email: str = "admin@company.com"

    auto_pause_days: int = 14
    archive_after_inactive_days: int = 14


settings = Settings()
