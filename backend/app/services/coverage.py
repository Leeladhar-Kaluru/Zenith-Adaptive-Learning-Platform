"""What is actually available, per class and subject, and the way a student asks for more.

Every number is counted from the database. A subject with nothing published says so; nothing is hidden or padded."""
from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Chapter, Concept, IngestJob, JobRequester, Lesson, LessonConcept, LessonVersion, Profile, Subject

MAX_TOPIC = 120


class CoverageError(ValueError):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def _covered_concepts(db: Session) -> set[str]:
    """Concepts that have at least one published lesson."""
    return {c for (c,) in db.execute(select(LessonConcept.concept_id).join(LessonVersion, and_(LessonVersion.lesson_id == LessonConcept.lesson_id, LessonVersion.status == "published")).distinct())}


def missing_concepts(db: Session, grade: int, subject_id: str) -> list[Concept]:
    """Concepts declared for this class and subject that no published lesson teaches yet."""
    covered = _covered_concepts(db)
    return [c for c in db.scalars(select(Concept).where(Concept.grade == grade, Concept.subject_id == subject_id, Concept.enrichment.is_(False)).order_by(Concept.title)) if c.id not in covered]


def table(db: Session, grade: int | None = None) -> list[dict]:
    """One row per class and subject: published chapters and lessons, topics with and without lessons, and what is waiting for review."""
    covered = _covered_concepts(db)
    names = dict(db.execute(select(Subject.id, Subject.name)).all())
    cells: dict[tuple[int, str], dict] = {}

    def cell(g: int, s: str) -> dict:
        return cells.setdefault((g, s), {"grade": g, "subject": s, "name": names.get(s, s), "chapters": 0, "lessons": 0, "topics": 0, "topicsCovered": 0, "inReview": 0, "requested": 0})

    for c in db.scalars(select(Concept).where(Concept.enrichment.is_(False))):
        if grade and c.grade != grade:
            continue
        x = cell(c.grade, c.subject_id)
        x["topics"] += 1
        x["topicsCovered"] += int(c.id in covered)
    for g, s, n in db.execute(select(Chapter.grade, Chapter.subject_id, func.count(Chapter.id)).where(Chapter.status == "published").group_by(Chapter.grade, Chapter.subject_id)):
        if not grade or g == grade:
            cell(g, s)["chapters"] = n
    for g, s, n in db.execute(select(Chapter.grade, Chapter.subject_id, func.count(func.distinct(Lesson.id))).join(Lesson, Lesson.chapter_id == Chapter.id)
                              .join(LessonVersion, and_(LessonVersion.lesson_id == Lesson.id, LessonVersion.status == "published")).group_by(Chapter.grade, Chapter.subject_id)):
        if not grade or g == grade:
            cell(g, s)["lessons"] = n
    for g, s, n in db.execute(select(Chapter.grade, Chapter.subject_id, func.count(func.distinct(Lesson.id))).join(Lesson, Lesson.chapter_id == Chapter.id)
                              .join(LessonVersion, and_(LessonVersion.lesson_id == Lesson.id, LessonVersion.status.in_(("in_review", "approved")))).group_by(Chapter.grade, Chapter.subject_id)):
        if not grade or g == grade:
            cell(g, s)["inReview"] = n
    for g, s, n in db.execute(select(IngestJob.grade, IngestJob.subject_id, func.count(IngestJob.id)).where(IngestJob.kind == "request", IngestJob.status.in_(("queued", "running", "blocked"))).group_by(IngestJob.grade, IngestJob.subject_id)):
        if g and s and (not grade or g == grade):
            cell(g, s)["requested"] = n
    return sorted(cells.values(), key=lambda r: (r["grade"], r["name"]))


def for_student(db: Session, p: Profile) -> dict:
    rows = table(db, p.grade)
    mine = {(r[0], r[1]) for r in db.execute(select(IngestJob.grade, IngestJob.subject_id).join(JobRequester, JobRequester.job_id == IngestJob.id)
                                              .where(JobRequester.student_id == p.id, IngestJob.kind == "request", IngestJob.status != "done"))}
    for r in rows:
        r["youRequested"] = (r["grade"], r["subject"]) in mine
        r["missingTopics"] = [c.title for c in missing_concepts(db, r["grade"], r["subject"])][:8]
    return {"grade": p.grade, "rows": rows}


def request_lessons(db: Session, p: Profile, subject_id: str, topic: str | None = None) -> dict:
    """A student asks for more lessons in a subject of their own class. One person counts once per request, however often they press the button."""
    if p.role != "student" or not p.grade:
        raise CoverageError("Only students in a class can ask for lessons.", 403)
    if db.get(Subject, subject_id) is None:
        raise CoverageError("Unknown subject.")
    topic = (topic or "").strip()[:MAX_TOPIC] or None
    job = db.scalar(select(IngestJob).where(IngestJob.kind == "request", IngestJob.grade == p.grade, IngestJob.subject_id == subject_id,
                                            IngestJob.topic.is_(topic) if topic is None else IngestJob.topic == topic, IngestJob.status.in_(("queued", "running", "blocked"))))
    if job is None:
        job = IngestJob(kind="request", grade=p.grade, subject_id=subject_id, topic=topic, demand=0)
        db.add(job)
        db.flush()
    if db.get(JobRequester, (job.id, p.id)) is None:
        db.add(JobRequester(job_id=job.id, student_id=p.id))
        db.flush()
    job.demand = db.scalar(select(func.count()).select_from(JobRequester).where(JobRequester.job_id == job.id)) or 1
    db.commit()
    return {"id": str(job.id), "demand": job.demand, "status": job.status}
