"""Teacher workspace, content review and the Ask tutor."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cms import review as review_svc
from app.core.database import get_db
from app.core.security import get_profile, reviewer_only, teacher_only
from app.models import Chapter, Concept, GateResult, Lesson, LessonVersion, Profile, Subject, Board
from app.services import accounts, library, teacher as T, tutor
from app.core.security import student_only

router = APIRouter()


def _t(fn, *a, **k):
    try:
        return fn(*a, **k)
    except (T.TeacherError, review_svc.ReviewError) as e:
        raise HTTPException(getattr(e, "status", 422), str(e))


# ---- teacher -------------------------------------------------------------------------------------
class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    grade: int
    subject: str


@router.get("/teacher/classes")
def classes(t: Profile = Depends(teacher_only), db: Session = Depends(get_db)):
    from app.models import Classroom
    return [T.summary(db, c) for c in db.scalars(select(Classroom).where(Classroom.teacher_id == t.id).order_by(Classroom.created_at))]


@router.post("/teacher/classes")
def create_class(body: ClassIn, t: Profile = Depends(teacher_only), db: Session = Depends(get_db)):
    if not db.get(Subject, body.subject):
        raise HTTPException(422, "Choose a subject from the list.")
    return T.summary(db, _t(T.create_class, db, t, body.name, body.grade, body.subject))


@router.get("/teacher/classes/{class_id}")
def class_overview(class_id: uuid.UUID, t: Profile = Depends(teacher_only), db: Session = Depends(get_db)):
    return _t(T.overview, db, t, class_id)


class LeaguesIn(BaseModel):
    enabled: bool


@router.put("/teacher/classes/{class_id}/leagues")
def leagues(class_id: uuid.UUID, body: LeaguesIn, t: Profile = Depends(teacher_only), db: Session = Depends(get_db)):
    return _t(T.set_leagues, db, t, class_id, body.enabled)


@router.get("/teacher/classes/{class_id}/students/{student_id}")
def student(class_id: uuid.UUID, student_id: uuid.UUID, t: Profile = Depends(teacher_only), db: Session = Depends(get_db)):
    return _t(T.student_detail, db, t, class_id, student_id)


class AssignIn(BaseModel):
    classId: uuid.UUID
    kind: str = Field(pattern="^(lesson|practice|test|revision)$")
    chapter: Optional[str] = None
    lessonId: Optional[uuid.UUID] = None
    conceptIds: list[str] = []
    due: Optional[datetime] = None
    note: Optional[str] = Field(None, max_length=300)
    suggestionKey: Optional[str] = None
    studentIds: list[uuid.UUID] = []


@router.post("/teacher/assignments")
def assign_work(body: AssignIn, t: Profile = Depends(teacher_only), db: Session = Depends(get_db)):
    a = _t(T.create_assignment, db, t, body.classId, kind=body.kind, chapter=body.chapter, lesson_id=body.lessonId, concept_ids=body.conceptIds,
           due=body.due, note=body.note, suggestion_key=body.suggestionKey, student_ids=body.studentIds)
    return {"id": str(a.id), "title": a.title}


class DecideIn(BaseModel):
    key: str
    action: str
    note: Optional[str] = None


@router.post("/teacher/classes/{class_id}/decisions")
def decide(class_id: uuid.UUID, body: DecideIn, t: Profile = Depends(teacher_only), db: Session = Depends(get_db)):
    _t(T.decide, db, t, class_id, body.key, body.action, body.note)
    return {"ok": True}


@router.get("/teacher/catalog")
def catalog(grade: int, subject: str, t: Profile = Depends(teacher_only), db: Session = Depends(get_db)):
    """Published chapters and lessons a teacher can assign."""
    out = []
    for ch in db.scalars(select(Chapter).where(Chapter.grade == grade, Chapter.subject_id == subject, Chapter.status == "published").order_by(Chapter.sort_order, Chapter.number.nulls_last())):
        out.append({"slug": ch.slug, "title": ch.title, "lessons": [{"id": str(l.id), "title": v.title} for l, v in library._published_lessons(db, ch.id)]})
    return out


# ---- review (content management) -----------------------------------------------------------------
@router.get("/review/queue")
def queue(status: Optional[str] = None, r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    q = select(LessonVersion, Lesson, Chapter).join(Lesson, Lesson.id == LessonVersion.lesson_id).join(Chapter, Chapter.id == Lesson.chapter_id)
    q = q.where(LessonVersion.status == status) if status else q.where(LessonVersion.status.in_(("draft", "in_review", "changes_requested", "approved")))
    out = []
    for lv, l, ch in db.execute(q.order_by(Chapter.grade, Chapter.slug, Lesson.position, LessonVersion.version.desc())):
        gates = review_svc.gate_summary(db, lv.id)
        out.append({"id": str(lv.id), "title": lv.title, "chapter": f"Class {ch.grade} · {ch.title}", "grade": ch.grade, "subject": ch.subject_id, "status": lv.status,
                    "version": lv.version, "origin": lv.origin, "gates": {"passed": sum(1 for g in gates if g.passed), "total": len(gates)}})
    return out


@router.get("/review/lessons/{version_id}")
def review_detail(version_id: uuid.UUID, r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    lv = db.get(LessonVersion, version_id)
    if lv is None:
        raise HTTPException(404, "Lesson version not found.")
    les = db.get(Lesson, lv.lesson_id)
    ch = db.get(Chapter, les.chapter_id)
    gates = review_svc.gate_summary(db, lv.id)
    payload = library.lesson_payload(db, r, les.id, version_id=lv.id)
    cv_verified = None
    return {"id": str(lv.id), "title": lv.title, "chapter": f"Class {ch.grade} · {ch.title}", "status": lv.status, "version": lv.version, "origin": lv.origin,
            "reviewNote": lv.review_note, "gates": [{"name": g.name, "passed": g.passed, "detail": g.detail, "manual": g.manual} for g in gates],
            "flags": lv.ai_flags or [], "lesson": payload, "answers": _answer_key(db, lv)}


def _answer_key(db: Session, lv: LessonVersion) -> list[dict]:
    from app.models import Item, LessonVersionItem
    rows = db.scalars(select(Item).join(LessonVersionItem, LessonVersionItem.item_id == Item.id).where(LessonVersionItem.lesson_version_id == lv.id).order_by(LessonVersionItem.position))
    return [{"key": i.key, "kind": i.kind, "stem": i.stem, "difficulty": i.difficulty, "purpose": i.purpose, "answer": i.answer_spec, "explanation": i.explanation} for i in rows]


class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(approve|publish|approve_publish|changes|archive)$")
    comment: Optional[str] = None
    manualGatesConfirmed: bool = False


@router.post("/review/lessons/{version_id}")
def decide_version(version_id: uuid.UUID, body: DecisionIn, r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    d = body.decision
    if d in ("approve", "approve_publish"):
        _t(review_svc.approve, db, version_id, r.id, body.manualGatesConfirmed)
    if d in ("publish", "approve_publish"):
        _t(review_svc.publish, db, version_id, r.id)
    if d == "changes":
        _t(review_svc.request_changes, db, version_id, r.id, body.comment or "")
    if d == "archive":
        _t(review_svc.archive, db, version_id, r.id)
    db.commit()
    return {"ok": True, "status": db.get(LessonVersion, version_id).status}


@router.post("/review/lessons/{version_id}/ai-review")
async def ai_review(version_id: uuid.UUID, r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    """Ask the AI to read the lesson as a teacher would. It returns flags only; it can never approve."""
    from app.cms.ai_review import run
    lv = db.get(LessonVersion, version_id)
    if lv is None:
        raise HTTPException(404, "Lesson version not found.")
    flags = await run(db, lv)
    lv.ai_flags = flags
    db.commit()
    return {"flags": flags}


@router.get("/review/assets-due")
def assets_due(r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    """Imported assets whose licence re-check date has passed. Retire any whose terms changed."""
    from app.ingest.recheck import due_for_recheck
    return {"assets": [{"id": str(a.id), "externalId": a.external_id, "licence": a.licence_id, "url": a.url, "kind": a.kind, "recheckAt": a.recheck_at.isoformat()} for a in due_for_recheck(db)]}


@router.get("/review/coverage")
def coverage(r: Profile = Depends(reviewer_only), db: Session = Depends(get_db)):
    """What is live, what is waiting, per chapter: so nobody claims coverage that is not real."""
    out = []
    for ch in db.scalars(select(Chapter).where(Chapter.status != "archived").order_by(Chapter.grade, Chapter.subject_id, Chapter.slug)):
        lessons = db.scalars(select(Lesson).where(Lesson.chapter_id == ch.id)).all()
        live = sum(1 for l in lessons if db.scalar(select(LessonVersion.id).where(LessonVersion.lesson_id == l.id, LessonVersion.status == "published")))
        out.append({"slug": ch.slug, "title": ch.title, "grade": ch.grade, "subject": ch.subject_id, "status": ch.status, "lessons": len(lessons), "published": live})
    return out


# ---- tutor ---------------------------------------------------------------------------------------
class AskIn(BaseModel):
    message: str = Field(min_length=1, max_length=600)
    lessonId: Optional[uuid.UUID] = None
    language: str = "en"
    clientId: Optional[str] = Field(default=None, min_length=8, max_length=64)      # set by the app so a retried offline question is answered once


@router.post("/tutor/ask")
async def ask(body: AskIn, p: Profile = Depends(student_only), db: Session = Depends(get_db)):
    if p.consent_status not in ("granted", "not_required"):
        raise HTTPException(403, "A parent, guardian or school needs to agree first.")
    try:
        return await tutor.ask(db, p, body.message, body.lessonId, body.language, body.clientId)
    except tutor.TutorLimit:
        raise HTTPException(429, "You have asked a lot of questions today. Try again tomorrow, or reread the lesson.")
    except ValueError as e:
        raise HTTPException(422, str(e))
