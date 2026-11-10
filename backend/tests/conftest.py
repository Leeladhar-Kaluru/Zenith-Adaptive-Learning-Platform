import os
import uuid

import pytest

# Tests run against Supabase, in their own schema (zenith_test). They TRUNCATE tables, so they must never see real data.
from dotenv import dotenv_values  # noqa: E402

_url = os.environ.get("SETU_TEST_DATABASE_URL") or dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".env")).get("DATABASE_URL")
if not _url:
    raise RuntimeError("Set SETU_TEST_DATABASE_URL, or DATABASE_URL in backend/.env (a Supabase connection string).")
os.environ["DATABASE_URL"] = _url
os.environ["DB_SCHEMA"] = "zenith_test"
os.environ["APP_ENV"] = "test"
os.environ["ZENITH_DEV_AUTH"] = "true"
os.environ["ENABLE_REMOTE_AI"] = "false"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SECRET_KEY"] = ""
os.environ["SUPABASE_PUBLISHABLE_KEY"] = ""
os.environ["GROQ_API_KEY"] = ""

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import dev_token  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Board, Profile, Subject  # noqa: E402

KEEP = {"alembic_version"}
assert os.environ["DB_SCHEMA"] == "zenith_test", "tests must only ever run in the zenith_test schema"


@pytest.fixture(scope="session", autouse=True)
def migrated():
    backend = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg = Config(os.path.join(backend, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend, "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture()
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
        names = [t.name for t in Base.metadata.sorted_tables if t.name not in KEEP]
        with engine.begin() as c:
            c.execute(text("TRUNCATE TABLE " + ", ".join(f'"zenith_test"."{n}"' for n in names) + " RESTART IDENTITY CASCADE"))


@pytest.fixture()
def client(db):
    return TestClient(app)


def make_profile(db, role="student", grade=7, nickname=None, **kw) -> Profile:
    if not db.get(Board, "cbse"):
        db.add(Board(id="cbse", name="CBSE"))
    for sid, name in (("maths", "Mathematics"), ("science", "Science")):
        if not db.get(Subject, sid):
            db.add(Subject(id=sid, name=name))
    db.flush()
    p = Profile(id=uuid.uuid4(), email=f"{uuid.uuid4().hex[:8]}@example.test", role=role, display_name="Test User",
                nickname=nickname or f"nick{uuid.uuid4().hex[:4]}", avatar="fox", grade=grade if role == "student" else None,
                board_id="cbse", language="en", onboarding_completed=True, consent_status="granted", **kw)
    db.add(p)
    db.commit()
    return p


def auth(p: Profile) -> dict:
    return {"Authorization": f"Bearer {dev_token(p.id)}"}
