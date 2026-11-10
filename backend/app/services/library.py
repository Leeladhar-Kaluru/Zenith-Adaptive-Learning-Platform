"""Student-facing curriculum browsing. Only published content ever leaves this module."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.memo import memo
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.engine import graph
from app.models import (Card, Chapter, ChapterConcept, Concept, CurriculumVersion, EvidenceEvent, Item, Lesson, LessonConcept,
                        LessonProgress, LessonVersion, LessonVersionItem, Profile)
from app.services import items as item_svc
from app.services import states as st_svc


class NotFound(LookupError):
    pass


def _all_published_lessons(db: Session) -> dict[uuid.UUID, list[tuple[Lesson, LessonVersion]]]:
    """Every published lesson of every chapter in one query, in lesson order (shared by all chapter cards in a request)."""
    def load():
        out: dict[uuid.UUID, list[tuple[Lesson, LessonVersion]]] = {}
        for l, v in db.execute(select(Lesson, LessonVersion).join(LessonVersion, LessonVersion.lesson_id == Lesson.id)
                               .where(LessonVersion.status == "published", LessonVersion.language == "en").order_by(Lesson.position)):
            out.setdefault(l.chapter_id, []).append((l, v))
        return out
    return memo(db, "published_lessons", load)


def _published_lessons(db: Session, chapter_id: uuid.UUID, language: str = "en") -> list[tuple[Lesson, LessonVersion]]:
    return list(_all_published_lessons(db).get(chapter_id, []))


def chapter_concept_ids(db: Session, chapter_id: uuid.UUID) -> list[str]:
    """Topic ids of a chapter. All chapters are loaded in one query the first time, then served from memory for the request."""
    def load():
        out: dict[uuid.UUID, list[str]] = {}
        for cid, concept in db.execute(select(ChapterConcept.chapter_id, ChapterConcept.concept_id)):
            out.setdefault(cid, []).append(concept)
        return out
    return list(memo(db, "chapter_concepts", load).get(chapter_id, []))


def progress_rows(db: Session, student_id: uuid.UUID) -> list[tuple[uuid.UUID, str]]:
    """The student's lesson progress, most recent first, loaded once per request and shared by every page section."""
    def load():
        return [(lid, st) for lid, st in db.execute(select(LessonProgress.lesson_id, LessonProgress.status).where(LessonProgress.student_id == student_id)
                                                     .order_by(LessonProgress.updated_at.desc().nulls_last(), LessonProgress.started_at.desc()))]
    return list(memo(db, ("progress_rows", student_id), load))


def _progress_map(db: Session, student_id: uuid.UUID) -> dict[uuid.UUID, str]:
    return dict(progress_rows(db, student_id))


def chapter_card(db: Session, ch: Chapter, student_id: uuid.UUID | None, prog: dict) -> dict:
    lessons = _published_lessons(db, ch.id)
    published = ch.status == "published"
    done = sum(1 for l, _ in lessons if prog.get(l.id) == "completed")
    concepts = len(chapter_concept_ids(db, ch.id))
    return {"id": str(ch.id), "slug": ch.slug, "grade": ch.grade, "subject": ch.subject_id, "number": ch.number, "title": ch.title,
            "status": "published" if published else "coming_soon", "lessonCount": len(lessons) if published else 0,
            "conceptCount": concepts if published else 0,
            "progress": {"done": done, "total": len(lessons)} if (published and student_id) else None}


def chapters(db: Session, profile: Profile, grade: int | None, subject: str | None) -> list[dict]:
    q = (select(Chapter).join(CurriculumVersion, CurriculumVersion.id == Chapter.version_id)
         .where(Chapter.status != "archived", CurriculumVersion.board_id == (profile.board_id or "cbse")))
    if grade:
        q = q.where(Chapter.grade == grade)
    if subject:
        q = q.where(Chapter.subject_id == subject)
    prog = _progress_map(db, profile.id)
    out = [chapter_card(db, c, profile.id, prog) for c in db.scalars(q.order_by(Chapter.grade, Chapter.sort_order, Chapter.number.nulls_last(), Chapter.title))]
    return out


def _lesson_for_concept(db: Session, concept_id: str) -> dict | None:
    row = db.execute(select(Lesson.id, LessonVersion.title, Chapter.slug).join(LessonConcept, LessonConcept.lesson_id == Lesson.id)
                     .join(LessonVersion, and_(LessonVersion.lesson_id == Lesson.id, LessonVersion.status == "published", LessonVersion.language == "en"))
                     .join(Chapter, Chapter.id == Lesson.chapter_id).where(LessonConcept.concept_id == concept_id)
                     .order_by(Chapter.grade, Lesson.position).limit(1)).first()
    return {"lessonId": str(row[0]), "title": row[1], "chapterSlug": row[2]} if row else None


def prerequisite_view(db: Session, student_id: uuid.UUID, concept_ids: list[str], exclude: set[str]) -> list[dict]:
    e = st_svc.edges(db)
    seen: dict[str, int] = {}
    for c in concept_ids:
        for a, d in graph.ancestors(c, e, 3):
            if a not in exclude:
                seen[a] = min(seen.get(a, 9), d)
    stt = st_svc.states(db, student_id, list(seen))
    out = []
    for a, d in sorted(seen.items(), key=lambda kv: kv[1]):
        c = db.get(Concept, a)
        lesson = _lesson_for_concept(db, a)
        out.append({"conceptId": a, "title": c.title, "grade": c.grade, "band": st_svc.band(stt.get(a)),
                    "lessonId": lesson["lessonId"] if lesson else None, "distance": d})
    return out


def chapter_detail(db: Session, profile: Profile, slug: str) -> dict:
    ch = db.scalar(select(Chapter).where(Chapter.slug == slug))
    if ch is None or ch.status == "archived":
        raise NotFound("Chapter not found.")
    prog = _progress_map(db, profile.id)
    card = chapter_card(db, ch, profile.id, prog)
    lessons_out, objectives, first_todo = [], [], None
    if ch.status == "published":
        for l, v in _published_lessons(db, ch.id):
            state = "done" if prog.get(l.id) == "completed" else "todo"
            lessons_out.append({"id": str(l.id), "title": v.title, "order": l.position, "minutes": v.minutes, "state": state})
            objectives += v.objectives
        for lo in lessons_out:
            if lo["state"] == "todo":
                lo["state"] = "current"
                break
    cids = chapter_concept_ids(db, ch.id)
    stt = st_svc.states(db, profile.id, cids)
    concepts = [{"id": c.id, "title": c.title, "band": st_svc.band(stt.get(c.id)), "evidence": stt.get(c.id, {}).get("n", 0)}
                for c in db.scalars(select(Concept).where(Concept.id.in_(cids)).order_by(Concept.title))]
    prereqs = prerequisite_view(db, profile.id, cids, set(cids)) if ch.status == "published" else []
    return {"chapter": card, "summary": ch.summary, "objectives": objectives, "lessons": lessons_out, "concepts": concepts, "prerequisites": prereqs}


def _state_label(prog: dict, lesson_id) -> str:
    return "done" if prog.get(lesson_id) == "completed" else "todo"


def _resolve_blocks(db: Session, lv: LessonVersion) -> list[dict]:
    items = {i.key: i for i in db.scalars(select(Item).join(LessonVersionItem, LessonVersionItem.item_id == Item.id)
                                          .where(LessonVersionItem.lesson_version_id == lv.id))}
    out = []
    for n, b in enumerate(lv.blocks):
        b = dict(b)
        b["id"] = f"b{n + 1}"
        if b["kind"] == "check":
            b["item"] = item_svc.public_item(items[b["item"]])
        out.append(b)
    return out


def lesson_payload(db: Session, profile: Profile, lesson_id: uuid.UUID, version_id: uuid.UUID | None = None) -> dict:
    """Published lesson for students. `version_id` previews an unpublished version for reviewers only (caller checks the role)."""
    # one joined lookup for the lesson, its chapter and the version to show
    base = select(Lesson, Chapter).join(Chapter, Chapter.id == Lesson.chapter_id).where(Lesson.id == lesson_id)
    row = db.execute(base).first()
    if row is None:
        raise NotFound("Lesson not found.")
    lesson, ch = row
    q = select(LessonVersion).where(LessonVersion.lesson_id == lesson.id)
    q = q.where(LessonVersion.id == version_id) if version_id else q.where(LessonVersion.status == "published", LessonVersion.language == "en")
    lv = db.scalar(q.limit(1))
    if lv is None:
        raise NotFound("This lesson is not available yet.")
    siblings = _published_lessons(db, ch.id)
    prog = _progress_map(db, profile.id)
    idx = next((i for i, (l, _) in enumerate(siblings) if l.id == lesson.id), None)
    prev_id = str(siblings[idx - 1][0].id) if idx not in (None, 0) else None
    next_id = str(siblings[idx + 1][0].id) if idx is not None and idx + 1 < len(siblings) else None
    cids = [c for (c,) in db.execute(select(LessonConcept.concept_id).where(LessonConcept.lesson_id == lesson.id))]
    gap = st_svc.root_gap(db, profile.id, cids)
    pre = None
    if gap:
        les = _lesson_for_concept(db, gap["concept"].id)
        pre = {"conceptId": gap["concept"].id, "title": gap["concept"].title, "grade": gap["concept"].grade, "band": gap["state"]["status"],
               "lessonId": les["lessonId"] if les else None}
    related = []
    for c in cids:
        for a, _ in graph.ancestors(c, st_svc.edges(db), 1):
            l = _lesson_for_concept(db, a)
            if l and l["lessonId"] != str(lesson.id) and l["lessonId"] not in [r["lessonId"] for r in related]:
                related.append({**l, "why": "Builds on this idea"})
    return {"id": str(lesson.id), "versionId": str(lv.id), "chapterSlug": ch.slug, "chapterTitle": ch.title, "subject": ch.subject_id,
            "title": lv.title, "order": lesson.position, "total": len(siblings), "minutes": lv.minutes, "objectives": lv.objectives,
            "prevId": prev_id, "nextId": next_id, "prereqGap": pre, "blocks": _resolve_blocks(db, lv),
            "siblings": [{"id": str(l.id), "title": v.title, "order": l.position, "minutes": v.minutes, "state": _state_label(prog, l.id)} for l, v in siblings],
            "related": related[:4], "completed": prog.get(lesson.id) == "completed"}


def complete_lesson(db: Session, profile: Profile, lesson_id: uuid.UUID) -> dict:
    """Mark complete only when the student has answered every understanding check in the lesson."""
    lv = db.scalar(select(LessonVersion).where(LessonVersion.lesson_id == lesson_id, LessonVersion.status == "published", LessonVersion.language == "en"))
    if lv is None:
        raise NotFound("Lesson not found.")
    check_keys = {b["item"] for b in lv.blocks if b["kind"] == "check"}
    ids = [i for (i,) in db.execute(select(Item.id).join(LessonVersionItem, LessonVersionItem.item_id == Item.id)
                                    .where(LessonVersionItem.lesson_version_id == lv.id, Item.key.in_(check_keys)))]
    answered = {i for (i,) in db.execute(select(EvidenceEvent.item_id).where(EvidenceEvent.student_id == profile.id, EvidenceEvent.item_id.in_(ids)))}
    if len(answered) < len(ids):
        raise ValueError(f"Answer the {len(ids) - len(answered)} remaining understanding check(s) first.")
    now = datetime.now(timezone.utc)
    row = db.get(LessonProgress, (profile.id, lesson_id))
    first = row is None or row.status != "completed"
    if row is None:
        row = LessonProgress(student_id=profile.id, lesson_id=lesson_id)
        db.add(row)
    row.status, row.completed_at, row.updated_at = "completed", row.completed_at or now, now
    db.flush()
    return {"completed": True, "first": first}


def search(db: Session, profile: Profile, q: str, grade: int | None, all_grades: bool) -> dict:
    q = q.strip()
    if len(q) < 2:
        return {"chapters": [], "lessons": [], "concepts": []}
    tsq = func.plainto_tsquery("simple", q)
    like = f"%{q}%"
    g = None if all_grades else (grade or profile.grade)
    ch_vec = func.to_tsvector("simple", func.coalesce(Chapter.title, "") + " " + func.coalesce(Chapter.summary, ""))
    cq = (select(Chapter).join(CurriculumVersion, CurriculumVersion.id == Chapter.version_id)
          .where(Chapter.status != "archived", CurriculumVersion.board_id == (profile.board_id or "cbse"), or_(ch_vec.op("@@")(tsq), Chapter.title.ilike(like))))
    if g:
        cq = cq.where(Chapter.grade == g)
    prog = _progress_map(db, profile.id)
    chapters_out = [chapter_card(db, c, profile.id, prog) for c in db.scalars(cq.limit(10))]
    lq = (select(Lesson.id, LessonVersion.title, Chapter.title, Chapter.grade).join(LessonVersion, and_(LessonVersion.lesson_id == Lesson.id, LessonVersion.status == "published"))
          .join(Chapter, Chapter.id == Lesson.chapter_id).join(CurriculumVersion, CurriculumVersion.id == Chapter.version_id)
          .where(CurriculumVersion.board_id == (profile.board_id or "cbse"), or_(func.to_tsvector("simple", LessonVersion.title).op("@@")(tsq), LessonVersion.title.ilike(like))))
    if g:
        lq = lq.where(Chapter.grade == g)
    lessons_out = [{"id": str(i), "title": t, "chapter": c, "grade": gr} for i, t, c, gr in db.execute(lq.limit(10))]
    kq = select(Concept).where(or_(func.to_tsvector("simple", Concept.title + " " + Concept.description).op("@@")(tsq), Concept.title.ilike(like)))
    if g:
        kq = kq.where(Concept.grade <= g)
    concepts_out = []
    for c in db.scalars(kq.limit(8)):
        les = _lesson_for_concept(db, c.id)
        concepts_out.append({"id": c.id, "title": c.title, "grade": c.grade, "lessonId": les["lessonId"] if les else None})
    return {"chapters": chapters_out, "lessons": lessons_out, "concepts": concepts_out}
