import os
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Supabase's session-mode pooler caps the whole project at 15 clients. Each
# process keeps a small pool (API 2+2, worker 1+1 via POOL_SIZE env) so the
# API, the worker, and short-lived scripts never exhaust the shared cap.
_SCHEMA = settings.DB_SCHEMA
if not _SCHEMA.replace("_", "").isalnum():
    raise RuntimeError("DB_SCHEMA must be letters, digits and underscores only")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "prepare_threshold": None,
        "options": "-c idle_in_transaction_session_timeout=15000",
    },
    # A liveness query before every checkout costs one database round trip per request. On Vercel (short-lived, same-region
    # functions) pool_recycle already retires old connections, so skip it there and keep it elsewhere.
    pool_pre_ping=not bool(os.environ.get("VERCEL")),
    pool_recycle=60,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_timeout=settings.POOL_TIMEOUT,
    pool_use_lifo=True,
    # Qualify every table with the schema in each statement. Works behind any pooler (including Supabase's
    # transaction pooler, which does not keep session state such as search_path).
    execution_options={"schema_translate_map": {None: _SCHEMA}},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            db.close()
        except Exception:
            pass

def check_db_health() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            return True
    except Exception:
        return False

