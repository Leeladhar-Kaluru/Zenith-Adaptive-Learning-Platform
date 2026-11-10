import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    APP_ENV: str = "local"
    SETU_TEST_AUTH: bool = False
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    DATABASE_URL: str
    # Sized for Supabase transaction pooler (port 6543)
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 5
    POOL_TIMEOUT: int = 30
    EMBEDDED_PIPELINE: bool = True
    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    
    # Storage settings
    STORAGE_BACKEND: str = "supabase"  # "supabase" or "local" (local is refused outside local/test)
    LOCAL_STORAGE_DIR: str = "local_storage"
    STORAGE_BUCKET_DOCUMENTS: str = "setu-documents"
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB — full textbooks exceed 50 MB
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "pptx", "txt", "md", "jpg", "jpeg", "png"]
    
    # AI and Embeddings configuration
    APP_NAME: str = "ZENITH"
    ENABLE_REMOTE_AI: bool = False
    LLM_PROVIDER: str = "groq"  # "groq", "lmstudio", "openai"
    GROQ_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_FALLBACK_MODEL: str = "qwen/qwen3.8-27b"
    EMBEDDING_BASE_URL: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-nomic-embed-text-v1.5"
    EMBEDDING_DIMENSION: int = 768

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

settings = Settings()

