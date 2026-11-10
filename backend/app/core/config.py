import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    APP_ENV: str = "local"
    ZENITH_DEV_AUTH: bool = False  # local/test only; ignored elsewhere
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    DATABASE_URL: str
    # All ZENITH tables live in this PostgreSQL schema (production: zenith; tests: zenith_test). Never the legacy public schema.
    DB_SCHEMA: str = "zenith"
    # Sized for Supabase transaction pooler (port 6543)
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 5
    POOL_TIMEOUT: int = 30
    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    
    # AI provider (Groq in production, LM Studio locally via LLM_PROVIDER=lmstudio)
    APP_NAME: str = "ZENITH"
    ENABLE_REMOTE_AI: bool = False
    LLM_PROVIDER: str = "groq"  # "groq", "lmstudio", "openai"
    GROQ_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_FALLBACK_MODEL: Optional[str] = None
    TUTOR_DAILY_LIMIT: int = 40
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

