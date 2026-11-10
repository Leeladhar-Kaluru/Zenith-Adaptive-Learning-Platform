"""Assignments from teachers, and how far each student has got with them."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (Assignment, AssessmentSession, Chapter, ChapterConcept, ClassMember, EvidenceEvent, ItemConcept, LessonProgress)

PRACTICE_TARGET = 5


def _concepts(db: Session, a: Assignment) -> list[str]:
    if a.concept_ids:
        return list(a.concept_ids)
    if a.chapter_id:
        return [c for (c,) in db.execute(select(ChapterConcept.concept_id).where(ChapterConcept.chapter_id == a.chapter_id))]
    return []


def progress(db: Session, student_id: uuid.UUID, a: Assignment) -> dict:
    ch = db.get(Chapter, a.chapter_id) if a.chapter_id else None
    if a.kind == "lesson":
        done = 1 if a.lesson_id and (db.scalar(select(LessonProgress.status).where(LessonProgress.student_id == student_id, LessonProgress.lesson_id == a.lesson_id)) == "completed") else 0
        return {"done": done, "total": 1, "href": f"/lesson/{a.lesson_id}"}
    if a.kind == "test":
        done = 1 if db.scalar(select(func.count(AssessmentSession.id)).where(AssessmentSession.student_id == student_id, AssessmentSession.assignment_id == a.id, AssessmentSession.status == "submitted")) else 0
        if a.concept_ids and not ch:
            return {"done": done, "total": 1, "href": f"/tests/new?kind=topic_test&concept={a.concept_ids[0]}&assignment={a.id}"}
        return {"done": done, "total": 1, "href": f"/tests/new?kind=chapter_test&chapter={ch.slug if ch else ''}&assignment={a.id}"}
    cids = _concepts(db, a)
    n = db.scalar(select(func.count(func.distinct(EvidenceEvent.id))).join(ItemConcept, ItemConcept.item_id == EvidenceEvent.item_id)
                  .where(EvidenceEvent.student_id == student_id, EvidenceEvent.occurred_at >= a.created_at, ItemConcept.concept_id.in_(cids or ["-"]))) or 0
    href = f"/practice?chapter={ch.slug}" if ch else (f"/practice?concept={cids[0]}" if cids else "/practice")
    return {"done": min(PRACTICE_TARGET, n), "total": PRACTICE_TARGET, "href": href}


def for_student(db: Session, student_id: uuid.UUID) -> list[dict]:
    rows = db.scalars(select(Assignment).join(ClassMember, ClassMember.classroom_id == Assignment.classroom_id)
                      .where(ClassMember.student_id == student_id, ClassMember.status == "active")
                      .order_by(Assignment.due_at.nulls_last(), Assignment.created_at.desc()))
    out = []
    for a in rows:
        p = progress(db, student_id, a)
        out.append({"id": str(a.id), "kind": a.kind, "title": a.title, "note": a.note, "due": a.due_at.isoformat() if a.due_at else None,
                    "done": p["done"], "total": p["total"], "href": p["href"], "complete": p["done"] >= p["total"], "why": a.reason})
    return out
