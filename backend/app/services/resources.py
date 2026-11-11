"""Class resources: documents and links a teacher shares with a class. Members read; only the owning teacher adds or removes."""
from __future__ import annotations

import uuid
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClassResource, Profile
from app.services import chatfiles
from app.services import classes as cls_svc
from app.services.classes import ClassError, plain

MAX_TITLE, MAX_NOTE, MAX_URL = 120, 500, 500


def dto(r: ClassResource) -> dict:
    a = r.attachment or {}
    return {"id": str(r.id), "kind": r.kind, "title": r.title, "note": r.note, "createdAt": r.created_at.isoformat(), "url": r.url if r.kind == "link" else None,
            "file": {"name": a.get("name"), "type": a.get("type"), "size": a.get("size")} if r.kind == "file" else None}


def listing(db: Session, c) -> list[dict]:
    return [dto(r) for r in db.scalars(select(ClassResource).where(ClassResource.classroom_id == c.id).order_by(ClassResource.created_at.desc()))]


def count(db: Session, class_id: uuid.UUID) -> int:
    return len(db.scalars(select(ClassResource.id).where(ClassResource.classroom_id == class_id)).all())


def _text(title: str, note: str) -> tuple[str, str]:
    t, n = plain(title), plain(note)
    if not t:
        raise ClassError("Give it a title.")
    if len(t) > MAX_TITLE or len(n) > MAX_NOTE:
        raise ClassError("The title or note is too long.")
    return t, n


def safe_url(url: str) -> str:
    """Plain http or https addresses only: no scripts, no data pages, no embedded passwords, no spaces."""
    u = (url or "").strip()
    if not u or len(u) > MAX_URL or any(ch.isspace() for ch in u):
        raise ClassError("That is not a web address I can use.")
    parts = urlsplit(u)
    if parts.scheme not in ("http", "https") or not parts.hostname or "." not in parts.hostname or parts.username or parts.password:
        raise ClassError("Use a full web address that starts with https://")
    return u


def add_link(db: Session, teacher: Profile, class_id: uuid.UUID, title: str, url: str, note: str = "") -> dict:
    c = cls_svc.owner_only(db, teacher, class_id)
    t, n = _text(title, note)
    r = ClassResource(classroom_id=c.id, author_id=teacher.id, kind="link", title=t, note=n, url=safe_url(url))
    db.add(r)
    db.commit()
    return dto(r)


def add_file(db: Session, teacher: Profile, class_id: uuid.UUID, filename: str, data: bytes, title: str, note: str = "") -> dict:
    c = cls_svc.owner_only(db, teacher, class_id)
    t, n = _text(title, note)
    try:
        info = chatfiles.validate(filename, data, office=True)
        key = chatfiles.new_key(c.id, info["ext"], chatfiles.FILES_PREFIX)
        chatfiles.put(key, data, info["type"])
    except chatfiles.FileError as e:
        raise ClassError(str(e), e.status)
    r = ClassResource(classroom_id=c.id, author_id=teacher.id, kind="file", title=t, note=n, attachment={"key": key, "name": info["name"], "type": info["type"], "size": info["size"]})
    db.add(r)
    db.commit()
    return dto(r)


def _get(db: Session, c, rid: uuid.UUID) -> ClassResource:
    r = db.get(ClassResource, rid)
    if r is None or r.classroom_id != c.id:
        raise ClassError("Not found.", 404)
    return r


def file_link(db: Session, p: Profile, class_id: uuid.UUID, rid: uuid.UUID) -> dict:
    r = _get(db, cls_svc.access(db, p, class_id), rid)
    if r.kind != "file" or not r.attachment:
        raise ClassError("Not found.", 404)
    try:
        return {"url": chatfiles.signed_url(r.attachment["key"]), "name": r.attachment["name"], "type": r.attachment["type"], "expiresIn": chatfiles.LINK_SECONDS}
    except chatfiles.FileError as e:
        raise ClassError(str(e), e.status)


def remove(db: Session, teacher: Profile, class_id: uuid.UUID, rid: uuid.UUID) -> dict:
    r = _get(db, cls_svc.owner_only(db, teacher, class_id), rid)
    db.delete(r)          # the stored file is no longer reachable: nobody can ask for a link to it
    db.commit()
    return {"deleted": True}
