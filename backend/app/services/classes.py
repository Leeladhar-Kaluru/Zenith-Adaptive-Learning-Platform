"""My Classes: what a student (or the owning teacher) sees inside a classroom. Membership is checked on every call.

A class you do not belong to answers 404, exactly like one that does not exist, so codes and ids cannot be probed."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Announcement, Assignment, ClassMember, Classroom, Profile

MAX_TITLE, MAX_BODY = 120, 4000
_SCRIPT = re.compile(r"<(script|style)\b.*?</\1\s*>", re.I | re.S)
_TAG = re.compile(r"<[^>]*>")


class ClassError(ValueError):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def plain(text: str) -> str:
    """Announcements are plain text: tags are removed and script/style content dropped, so nothing can render as markup."""
    text = _TAG.sub("", _SCRIPT.sub("", text or ""))
    return text.replace("<", "").replace(">", "").strip()


def _is_owner(p: Profile, c: Classroom) -> bool:
    return p.role == "admin" or (p.role == "teacher" and c.teacher_id == p.id)


def access(db: Session, p: Profile, class_id: uuid.UUID) -> Classroom:
    c = db.get(Classroom, class_id)
    if c is None:
        raise ClassError("Class not found.", 404)
    if _is_owner(p, c):
        return c
    m = db.get(ClassMember, (c.id, p.id)) if p.role == "student" else None
    if m is None or m.status != "active":
        raise ClassError("Class not found.", 404)
    return c


def owner_only(db: Session, p: Profile, class_id: uuid.UUID) -> Classroom:
    if p.role not in ("teacher", "admin"):
        raise ClassError("Only the class teacher can do this.", 403)
    return access(db, p, class_id)


def _upcoming(db: Session, c: Classroom) -> list[dict]:
    rows = db.scalars(select(Assignment).where(Assignment.classroom_id == c.id)
                      .order_by(Assignment.due_at.asc().nulls_last(), Assignment.created_at.desc()))
    return [{"id": str(a.id), "title": a.title, "kind": a.kind, "note": a.note, "dueAt": a.due_at.isoformat() if a.due_at else None,
             "href": f"/lesson/{a.lesson_id}" if a.lesson_id else None} for a in rows]


def _teacher(db: Session, c: Classroom) -> dict:
    t = db.get(Profile, c.teacher_id)
    return {"name": (t.display_name or "Your teacher") if t else "Your teacher", "avatar": t.avatar if t else None}


def _unread(db: Session, c: Classroom, p: Profile) -> int:
    from app.services import chat   # imported here: chat imports this module
    return chat.unread(db, p, c.id)


def _resource_count(db: Session, c: Classroom) -> int:
    from app.services import resources
    return resources.count(db, c.id)


def listing(db: Session, student: Profile) -> list[dict]:
    rows = db.scalars(select(Classroom).join(ClassMember, ClassMember.classroom_id == Classroom.id)
                      .where(ClassMember.student_id == student.id, ClassMember.status == "active").order_by(Classroom.name))
    out = []
    for c in rows:
        n = len(db.scalars(select(ClassMember.student_id).where(ClassMember.classroom_id == c.id, ClassMember.status == "active")).all())
        up = _upcoming(db, c)
        due = [a for a in up if a["dueAt"]]
        out.append({"id": str(c.id), "name": c.name, "grade": c.grade, "subject": c.subject_id, "teacher": _teacher(db, c), "classmates": n,
                    "nextDue": due[0] if due else None, "unread": _unread(db, c, student), "resources": _resource_count(db, c), "announcements": len(db.scalars(select(Announcement.id).where(Announcement.classroom_id == c.id)).all())})
    return out


def _classmates(db: Session, c: Classroom, viewer: Profile) -> list[dict]:
    """Nickname and avatar only. A classmate who opted out of competitive features shows as 'A classmate'."""
    people = db.scalars(select(Profile).join(ClassMember, ClassMember.student_id == Profile.id)
                        .where(ClassMember.classroom_id == c.id, ClassMember.status == "active"))
    out = []
    for m in people:
        me = m.id == viewer.id
        if m.league_opt_out and not me:
            out.append({"nickname": "A classmate", "avatar": None, "me": False})
        else:
            out.append({"nickname": m.nickname or "Student", "avatar": m.avatar, "me": me})
    out.sort(key=lambda x: (x["nickname"] == "A classmate", x["nickname"].lower()))
    return out


def _announcements(db: Session, c: Classroom) -> list[dict]:
    rows = db.scalars(select(Announcement).where(Announcement.classroom_id == c.id).order_by(Announcement.pinned.desc(), Announcement.created_at.desc())).all()
    names = {p.id: p.display_name for p in db.scalars(select(Profile).where(Profile.id.in_({r.author_id for r in rows if r.author_id})))} if rows else {}
    return [{"id": str(a.id), "title": a.title, "body": a.body, "pinned": a.pinned, "createdAt": a.created_at.isoformat(), "author": names.get(a.author_id, "Teacher")} for a in rows]


def open_reports(db: Session, c: Classroom) -> int:
    from app.models import ChatReport
    return len(db.scalars(select(ChatReport.id).where(ChatReport.classroom_id == c.id, ChatReport.status == "open")).all())


def _resources(db: Session, c: Classroom) -> list[dict]:
    from app.services import resources     # imported here: resources imports this module
    return resources.listing(db, c)


def detail(db: Session, viewer: Profile, class_id: uuid.UUID) -> dict:
    c = access(db, viewer, class_id)
    return {"id": str(c.id), "name": c.name, "grade": c.grade, "subject": c.subject_id, "teacher": _teacher(db, c), "isTeacher": _is_owner(viewer, c),
            "classmates": _classmates(db, c, viewer), "assignments": _upcoming(db, c), "announcements": _announcements(db, c),
            "resources": _resources(db, c), "openReports": open_reports(db, c) if _is_owner(viewer, c) else 0}


def leave(db: Session, student: Profile, class_id: uuid.UUID) -> dict:
    if student.role != "student":
        raise ClassError("Teachers manage a class from the teacher workspace.", 403)
    m = db.get(ClassMember, (class_id, student.id))
    if m is None or m.status != "active":
        raise ClassError("You are not in this class.", 404)
    m.status = "left"      # the record stays so the class history is intact; only access ends
    db.commit()
    return {"left": True}


def announce(db: Session, teacher: Profile, class_id: uuid.UUID, title: str, body: str, pinned: bool = False) -> dict:
    c = owner_only(db, teacher, class_id)
    title, body = plain(title), plain(body)
    if not title or not body:
        raise ClassError("Add a title and a message.")
    if len(title) > MAX_TITLE or len(body) > MAX_BODY:
        raise ClassError("That announcement is too long.")
    a = Announcement(classroom_id=c.id, author_id=teacher.id, title=title, body=body, pinned=pinned)
    db.add(a)
    db.commit()
    return {"id": str(a.id)}


def _announcement(db: Session, c: Classroom, ann_id: uuid.UUID) -> Announcement:
    a = db.get(Announcement, ann_id)
    if a is None or a.classroom_id != c.id:
        raise ClassError("Announcement not found.", 404)
    return a


def pin(db: Session, teacher: Profile, class_id: uuid.UUID, ann_id: uuid.UUID, pinned: bool) -> dict:
    a = _announcement(db, owner_only(db, teacher, class_id), ann_id)
    a.pinned = pinned
    db.commit()
    return {"pinned": a.pinned}


def remove(db: Session, teacher: Profile, class_id: uuid.UUID, ann_id: uuid.UUID) -> dict:
    a = _announcement(db, owner_only(db, teacher, class_id), ann_id)
    db.delete(a)
    db.commit()
    return {"deleted": True}
