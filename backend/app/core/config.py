import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field

class Settings(BaseSettings):
    APP_ENV: str = "local"
    ZENITH_DEV_AUTH: bool = False  # local/test only; ignored elsewhere
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    DATABASE_URL: str
    # All ZENITH tables live in this PostgreSQL schema (production: zenith; tests: zenith_test). Never the legacy public schema.
    BOT_VERSION: str = "1.1"   # version of our importer, sent in the User-Agent (not a secret)
    BOT_CONTACT: str = ""      # a real contact (email or URL) put in our crawler's User-Agent; Wikimedia refuses bots without one
    DB_SCHEMA: str = "zenith"
    # Sized for Supabase transaction pooler (port 6543)
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 5
    POOL_TIMEOUT: int = 30
    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    CRON_SECRET: str = ""        # shared secret the scheduler sends to /ingest/run; empty means the scheduled run is off
    
    # AI provider (Groq in production, LM Studio locally via LLM_PROVIDER=lmstudio)
    APP_NAME: str = "ZENITH"
    ENABLE_REMOTE_AI: bool = False
    LLM_PROVIDER: str = "groq"  # "groq", "lmstudio", "openai"
    GROQ_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_FALLBACK_MODEL: Optional[str] = None
    TUTOR_DAILY_LIMIT: int = 40
    # Backups (Backblaze B2, private bucket). The key id and bucket name are not secrets; the application key and BACKUP_KEY are.
    B2_KEY_ID: Optional[str] = None
    B2_APP_KEY: Optional[str] = Field(default=None, validation_alias=AliasChoices("B2_APP_KEY", "BACK_BLAZE_API_KEY"))
    B2_BUCKET: Optional[str] = None
    BACKUP_KEY: Optional[str] = None
    GIPHY_API_KEY: Optional[str] = None   # GIF search for class chat (server side only); GIFs are off without it
    XP_DAILY_CAP: int = 300

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

settings = Settings()

