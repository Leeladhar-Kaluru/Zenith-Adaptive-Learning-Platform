import os
import uuid

import pytest

_url = os.environ.get("SETU_TEST_DATABASE_URL")
if not _url:
    raise RuntimeError("SETU_TEST_DATABASE_URL is required (start backend/docker-compose.test.yml).")
os.environ["DATABASE_URL"] = _url
os.environ["APP_ENV"] = "test"
os.environ["ZENITH_DEV_AUTH"] = "true"
os.environ["ENABLE_REMOTE_AI"] = "false"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import dev_token  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Board, Profile, Subject  # noqa: E402

KEEP = {"alembic_version"}


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
            c.execute(text("TRUNCATE TABLE " + ", ".join(f'"{n}"' for n in names) + " RESTART IDENTITY CASCADE"))


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
