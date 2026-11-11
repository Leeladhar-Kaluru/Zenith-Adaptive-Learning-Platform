"""In-app notifications. Content-free by design: a title, one short line and a link inside the app. No personal data is put in them."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Notification, Profile

MAX_LIST = 30


def notify(db: Session, user_ids: list[uuid.UUID], kind: str, title: str, body: str = "", link: str | None = None, dedupe_key: str | None = None) -> int:
    """Create one notification per person. A repeated dedupe_key for the same person is ignored, so a retry never doubles a message."""
    if not user_ids:
        return 0
    rows = [dict(id=uuid.uuid4(), user_id=u, kind=kind, title=title[:120], body=body[:300], link=link, dedupe_key=dedupe_key) for u in dict.fromkeys(user_ids)]
    stmt = insert(Notification).values(rows).on_conflict_do_nothing(index_elements=["user_id", "dedupe_key"])
    return db.execute(stmt).rowcount or 0


def notify_grade(db: Session, grade: int, kind: str, title: str, body: str, link: str | None, dedupe_key: str) -> int:
    """Everyone studying in this class (grade) hears about it once."""
    ids = [i for (i,) in db.execute(select(Profile.id).where(Profile.role == "student", Profile.grade == grade, Profile.onboarding_completed.is_(True)))]
    return notify(db, ids, kind, title, body, link, dedupe_key)


def notify_role(db: Session, roles: tuple[str, ...], kind: str, title: str, body: str, link: str | None, dedupe_key: str) -> int:
    ids = [i for (i,) in db.execute(select(Profile.id).where(Profile.role.in_(roles)))]
    return notify(db, ids, kind, title, body, link, dedupe_key)


def listing(db: Session, p: Profile, limit: int = MAX_LIST) -> dict:
    rows = db.scalars(select(Notification).where(Notification.user_id == p.id).order_by(Notification.created_at.desc()).limit(max(1, min(limit, MAX_LIST)))).all()
    unread = db.scalar(select(func.count(Notification.id)).where(Notification.user_id == p.id, Notification.read_at.is_(None))) or 0
    return {"unread": unread, "items": [{"id": str(n.id), "kind": n.kind, "title": n.title, "body": n.body, "link": n.link, "at": n.created_at.isoformat(), "read": n.read_at is not None} for n in rows]}


def mark_read(db: Session, p: Profile, ids: list[uuid.UUID] | None = None) -> int:
    q = update(Notification).where(Notification.user_id == p.id, Notification.read_at.is_(None))
    if ids:
        q = q.where(Notification.id.in_(ids))
    n = db.execute(q.values(read_at=datetime.now(timezone.utc))).rowcount or 0
    db.commit()
    return n
