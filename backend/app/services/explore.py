"""Explore: the interactive experiences that really exist, found in published lessons. Nothing is listed unless a student can open it today."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Card, Chapter, Lesson, LessonVersion

SIMULATION = {"numberline", "balance", "fraction"}


def _kind(widget: str) -> str | None:
    if widget.startswith("sim_") or widget in SIMULATION:
        return "simulation"
    return {"data_chart": "data", "atlas": "map"}.get(widget)


def labs(db: Session, grade: int | None = None) -> list[dict]:
    rows = db.execute(select(Lesson.id, LessonVersion.title, LessonVersion.blocks, Chapter.slug, Chapter.title, Chapter.grade, Chapter.subject_id)
                      .join(LessonVersion, LessonVersion.lesson_id == Lesson.id).join(Chapter, Chapter.id == Lesson.chapter_id)
                      .where(LessonVersion.status == "published", LessonVersion.language == "en", Chapter.status == "published")
                      .order_by(Chapter.grade, Chapter.subject_id, Chapter.slug, Lesson.position)).all()
    out = []
    for lesson_id, title, blocks, slug, chapter, g, subject in rows:
        kinds = sorted({k for b in (blocks or []) if b.get("kind") == "widget" for k in [_kind(b.get("widget", ""))] if k})
        if kinds:
            out.append({"lessonId": str(lesson_id), "lessonTitle": title, "chapterSlug": slug, "chapterTitle": chapter, "grade": g, "subject": subject,
                        "kind": kinds[0], "kinds": kinds, "forYou": grade is not None and g == grade})
    out.sort(key=lambda r: (not r["forYou"], r["grade"], r["subject"], r["lessonTitle"]))
    return out


def available(db: Session) -> list[dict]:
    cards = db.scalar(select(func.count(Card.id)).join(LessonVersion, LessonVersion.id == Card.lesson_version_id).where(LessonVersion.status == "published")) or 0
    return [{"key": "flashcards", "title": "Flashcards", "text": "Revise key ideas with spaced repetition. Cards come back when you are about to forget them.", "href": "/revision", "count": cards}]
