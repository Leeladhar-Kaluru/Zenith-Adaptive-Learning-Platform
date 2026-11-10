"""Review workflow: draft -> in_review -> approved -> published -> archived. Humans decide; gates only inform."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Chapter, GateResult, Item, Lesson, LessonVersion, LessonVersionItem


class ReviewError(ValueError):
    pass


def _now():
    return datetime.now(timezone.utc)


def _audit(db: Session, actor: uuid.UUID, action: str, lv: LessonVersion, **detail):
    db.add(AuditLog(actor_id=actor, action=action, entity="lesson_version", entity_id=str(lv.id), detail={"version": lv.version, **detail}))


def gate_summary(db: Session, lv_id: uuid.UUID) -> list[GateResult]:
    return list(db.scalars(select(GateResult).where(GateResult.lesson_version_id == lv_id).order_by(GateResult.name)))


def approve(db: Session, lv_id: uuid.UUID, reviewer: uuid.UUID, manual_confirmed: bool = False) -> LessonVersion:
    lv = db.get(LessonVersion, lv_id)
    if lv is None:
        raise ReviewError("Lesson version not found.")
    if lv.status not in ("in_review", "changes_requested"):
        raise ReviewError(f"A {lv.status.replace('_', ' ')} lesson cannot be approved.")
    gates = gate_summary(db, lv.id)
    hard = [g.name for g in gates if not g.passed and not g.manual]
    if hard:
        raise ReviewError("These checks must pass first: " + ", ".join(hard))
    manual = [g for g in gates if not g.passed and g.manual]
    if manual and not manual_confirmed:
        raise ReviewError("Confirm the manual checks yourself before approving: " + ", ".join(g.name for g in manual))
    now = _now()
    for g in manual:
        g.acknowledged_by, g.passed, g.detail = reviewer, True, f"Confirmed by reviewer. {g.detail}".strip()
    lv.status, lv.reviewer_id, lv.reviewed_at = "approved", reviewer, now
    for item in db.scalars(select(Item).join(LessonVersionItem, LessonVersionItem.item_id == Item.id).where(LessonVersionItem.lesson_version_id == lv.id)):
        if item.status in ("draft", "in_review", "changes_requested"):
            item.status, item.reviewer_id, item.reviewed_at = "approved", reviewer, now
    _audit(db, reviewer, "content.approve", lv)
    db.flush()
    return lv


def publish(db: Session, lv_id: uuid.UUID, actor: uuid.UUID) -> LessonVersion:
    lv = db.get(LessonVersion, lv_id)
    if lv is None:
        raise ReviewError("Lesson version not found.")
    if lv.status != "approved" or lv.reviewer_id is None:
        raise ReviewError("Only an approved lesson can be published.")
    for old in db.scalars(select(LessonVersion).where(LessonVersion.lesson_id == lv.lesson_id, LessonVersion.language == lv.language,
                                                      LessonVersion.status == "published", LessonVersion.id != lv.id)):
        old.status = "archived"
    db.flush()
    lv.status, lv.published_at = "published", _now()
    for item in db.scalars(select(Item).join(LessonVersionItem, LessonVersionItem.item_id == Item.id).where(LessonVersionItem.lesson_version_id == lv.id)):
        item.status = "published"
    _audit(db, actor, "content.publish", lv)
    db.flush()
    refresh_chapter_status(db, db.get(Lesson, lv.lesson_id).chapter_id)
    return lv


def request_changes(db: Session, lv_id: uuid.UUID, reviewer: uuid.UUID, note: str) -> LessonVersion:
    lv = db.get(LessonVersion, lv_id)
    if lv is None or lv.status not in ("in_review", "approved"):
        raise ReviewError("This lesson is not waiting for review.")
    if len(note.strip()) < 3:
        raise ReviewError("Tell the author what to change.")
    lv.status, lv.review_note = "changes_requested", note.strip()
    _audit(db, reviewer, "content.changes_requested", lv, note=note.strip())
    db.flush()
    return lv


def archive(db: Session, lv_id: uuid.UUID, actor: uuid.UUID) -> LessonVersion:
    lv = db.get(LessonVersion, lv_id)
    if lv is None:
        raise ReviewError("Lesson version not found.")
    lv.status = "archived"
    _audit(db, actor, "content.archive", lv)
    db.flush()
    refresh_chapter_status(db, db.get(Lesson, lv.lesson_id).chapter_id)
    return lv


def refresh_chapter_status(db: Session, chapter_id: uuid.UUID) -> str:
    """A chapter is 'published' only when every one of its lessons has a published version."""
    chapter = db.get(Chapter, chapter_id)
    total = db.scalar(select(func.count(Lesson.id)).where(Lesson.chapter_id == chapter_id)) or 0
    live = db.scalar(select(func.count(func.distinct(LessonVersion.lesson_id))).join(Lesson, Lesson.id == LessonVersion.lesson_id)
                     .where(Lesson.chapter_id == chapter_id, LessonVersion.status == "published")) or 0
    chapter.status = "published" if total > 0 and live == total else ("archived" if chapter.status == "archived" else "in_production")
    db.flush()
    return chapter.status
