"""Teacher workspace: classes, evidence-grounded suggestions, assignments and interventions. Teachers decide; ZENITH notices."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.engine import bkt, graph
from app.models import (Assignment, AuditLog, Chapter, ChapterConcept, ClassMember, Classroom, Concept, ConceptLevel, ConceptState, EvidenceEvent, InteractionEvent,
                        Intervention, Item, Lesson, LessonProgress, LessonVersion, Profile, TeacherDecision)
from app.services import assign, home, library
from app.services import items as item_svc
from app.services import states as st_svc

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class TeacherError(ValueError):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def _now():
    return datetime.now(timezone.utc)


def _code(db: Session) -> str:
    for _ in range(20):
        c = "ZEN-" + "".join(secrets.choice(ALPHABET) for _ in range(4))
        if not db.scalar(select(Classroom.id).where(Classroom.join_code == c)):
            return c
    raise TeacherError("Could not make a class code. Try again.", 500)


def owned(db: Session, teacher: Profile, class_id: uuid.UUID) -> Classroom:
    c = db.get(Classroom, class_id)
    if c is None or (c.teacher_id != teacher.id and teacher.role != "admin"):
        raise TeacherError("Class not found.", 404)
    return c


def summary(db: Session, c: Classroom) -> dict:
    n = db.scalar(select(func.count(ClassMember.student_id)).where(ClassMember.classroom_id == c.id, ClassMember.status == "active")) or 0
    return {"id": str(c.id), "name": c.name, "grade": c.grade, "subject": c.subject_id, "students": n, "joinCode": c.join_code, "leaguesEnabled": c.leagues_enabled}


def create_class(db: Session, teacher: Profile, name: str, grade: int, subject: str) -> Classroom:
    if not 6 <= grade <= 10:
        raise TeacherError("Class must be between 6 and 10.")
    c = Classroom(teacher_id=teacher.id, name=name.strip()[:80] or f"Class {grade}", grade=grade, subject_id=subject, board_id=teacher.board_id or "cbse", join_code=_code(db))
    db.add(c)
    db.commit()
    return c


def join(db: Session, student: Profile, code: str) -> Classroom:
    c = db.scalar(select(Classroom).where(Classroom.join_code == code.strip().upper()))
    if c is None:
        raise TeacherError("That class code was not found. Check it with your teacher.", 404)
    if db.get(ClassMember, (c.id, student.id)) is None:
        db.add(ClassMember(classroom_id=c.id, student_id=student.id))
        db.commit()
    return c


def _members(db: Session, c: Classroom) -> list[Profile]:
    return list(db.scalars(select(Profile).join(ClassMember, ClassMember.student_id == Profile.id)
                           .where(ClassMember.classroom_id == c.id, ClassMember.status == "active").order_by(Profile.nickname, Profile.id)))


def _class_concepts(db: Session, c: Classroom) -> list[Concept]:
    ids = {x for (x,) in db.execute(select(ChapterConcept.concept_id).join(Chapter, Chapter.id == ChapterConcept.chapter_id)
                                    .where(Chapter.status == "published", Chapter.grade == c.grade, Chapter.subject_id == c.subject_id))}
    return list(db.scalars(select(Concept).where(Concept.id.in_(ids or {"-"})).order_by(Concept.title)))


def overview(db: Session, teacher: Profile, class_id: uuid.UUID) -> dict:
    c = owned(db, teacher, class_id)
    members = _members(db, c)
    concepts = _class_concepts(db, c)
    cids = [x.id for x in concepts]
    by_student = {m.id: st_svc.states(db, m.id) for m in members}
    heat = [{"id": str(m.id), "nickname": m.nickname or m.display_name, "avatar": m.avatar,
             "cells": [{"band": st_svc.band(by_student[m.id].get(cid)), "evidence": by_student[m.id].get(cid, {}).get("n", 0)} for cid in cids]} for m in members]
    need: list[dict] = []
    for m in members:
        weak = [(cid, s) for cid, s in by_student[m.id].items() if cid in cids and s["status"] in ("gap_confirmed", "gap_suspected") and s["n"] >= 2]
        if weak:
            cid, s = min(weak, key=lambda x: x[1]["p"])
            need.append({"id": str(m.id), "nickname": m.nickname or m.display_name, "avatar": m.avatar, "reason": f"{db.get(Concept, cid).title}: {s['c']} of {s['n']} answers right", "p": s["p"]})
    need.sort(key=lambda x: x["p"])
    decided = {d.suggestion_key for d in db.scalars(select(TeacherDecision).where(TeacherDecision.classroom_id == c.id))}
    return {"cls": summary(db, c), "concepts": [{"id": x.id, "title": x.title} for x in concepts], "heatmap": heat,
            "needsHelp": [{k: v for k, v in n.items() if k != "p"} for n in need[:6]],
            "suggestions": suggestions(db, c, members, by_student, decided), "trend": trend(db, [m.id for m in members]), "assignments": assignments(db, c, members)}


def suggestions(db: Session, c: Classroom, members: list[Profile], by_student: dict, decided: set[str]) -> list[dict]:
    """Class-level suggestions. A topic is flagged only when several students show real, repeated difficulty."""
    e = st_svc.edges(db)
    n = len(members)
    out = []
    cids = {x.id for x in _class_concepts(db, c)}
    for cid in cids:
        weak = [m for m in members if (s := by_student[m.id].get(cid)) and s["n"] >= 3 and s["p"] < 0.45]
        if len(weak) < max(2, round(0.25 * n)):
            continue
        roots: dict[str, int] = {}
        for m in weak:
            r = graph.investigate(cid, e, by_student[m.id])["root"]
            if r:
                roots[r] = roots.get(r, 0) + 1
        root = max(roots, key=roots.get) if roots and max(roots.values()) >= max(2, len(weak) // 2) else None
        target = root or cid
        key = f"{c.id}:{cid}:{target}"
        if key in decided:
            continue
        total = sum(by_student[m.id][cid]["n"] for m in weak)
        les = library._lesson_for_concept(db, target)
        title = db.get(Concept, cid).title
        text = f"{len(weak)} of {n} students repeatedly struggled with {title}."
        if root:
            text += f" For {roots[root]} of them the gap traces back to {db.get(Concept, root).title}."
        out.append({"key": key, "text": text, "evidence": f"{total} answers", "students": len(weak), "studentIds": [str(m.id) for m in weak], "conceptId": target,
                    "lessonId": les["lessonId"] if les else None, "lessonTitle": les["title"] if les else None})
    return sorted(out, key=lambda x: -x["students"])[:5]


def trend(db: Session, student_ids: list[uuid.UUID]) -> list[dict]:
    if not student_ids:
        return []
    since = _now() - timedelta(days=28)
    rows = db.execute(select(func.date(EvidenceEvent.occurred_at), func.count(), func.sum(cast(EvidenceEvent.correct, Integer)))
                      .where(EvidenceEvent.student_id.in_(student_ids), EvidenceEvent.occurred_at >= since).group_by(func.date(EvidenceEvent.occurred_at)).order_by(func.date(EvidenceEvent.occurred_at))).all()
    return [{"day": str(d), "answers": a, "accuracy": round((r or 0) / a, 3)} for d, a, r in rows]


def assignments(db: Session, c: Classroom, members: list[Profile]) -> list[dict]:
    out = []
    for a in db.scalars(select(Assignment).where(Assignment.classroom_id == c.id).order_by(Assignment.created_at.desc()).limit(10)):
        done = sum(1 for m in members if (p := assign.progress(db, m.id, a))["done"] >= p["total"])
        out.append({"id": str(a.id), "title": a.title, "kind": a.kind, "due": a.due_at.isoformat() if a.due_at else None, "done": done, "students": len(members)})
    return out


def learning_activity(db: Session, student_id: uuid.UUID, days: int = 14) -> dict:
    """What the student actually did in the last `days` days, counted from their recorded moves (no free text)."""
    since = _now() - timedelta(days=days)
    counts = dict(db.execute(select(InteractionEvent.kind, func.count()).where(InteractionEvent.student_id == student_id, InteractionEvent.occurred_at >= since)
                             .group_by(InteractionEvent.kind)).all())
    reading_ms = db.scalar(select(func.coalesce(func.sum(InteractionEvent.ms), 0)).where(InteractionEvent.student_id == student_id, InteractionEvent.kind == "dwell",
                                                                                       InteractionEvent.occurred_at >= since)) or 0
    return {"days": days, "readingMinutes": round(int(reading_ms) / 60000, 1), "lessonsOpened": counts.get("lesson_open", 0), "hintsOpened": counts.get("hint_open", 0),
            "answerChanges": counts.get("answer_change", 0), "simulationMoves": counts.get("sim_change", 0) + counts.get("sim_reset", 0)}


def levels(db: Session, student_id: uuid.UUID) -> list[dict]:
    """Where the student is on the 1-5 difficulty ladder per topic, with the stored reason for the last move."""
    out = []
    for lv in db.scalars(select(ConceptLevel).where(ConceptLevel.student_id == student_id).order_by(ConceptLevel.updated_at.desc())):
        c = db.get(Concept, lv.concept_id)
        out.append({"concept": lv.concept_id, "title": c.title if c else lv.concept_id, "level": lv.level, "reason": lv.reason, "updatedAt": lv.updated_at.isoformat()})
    return out


def student_detail(db: Session, teacher: Profile, class_id: uuid.UUID, student_id: uuid.UUID) -> dict:
    c = owned(db, teacher, class_id)
    if db.get(ClassMember, (c.id, student_id)) is None:
        raise TeacherError("Student not found in this class.", 404)
    s = db.get(Profile, student_id)
    stt = st_svc.states(db, student_id)
    concepts = [{"id": cd.id, "title": cd.title, "band": stt[cd.id]["status"], "evidence": stt[cd.id]["n"], "correct": stt[cd.id]["c"], "confidence": bkt.uncertainty(stt[cd.id]["n"])}
                for cd in db.scalars(select(Concept).where(Concept.id.in_(list(stt) or ["-"])).order_by(Concept.grade, Concept.title))]
    evs = db.scalars(select(EvidenceEvent).where(EvidenceEvent.student_id == student_id).order_by(EvidenceEvent.occurred_at.desc()).limit(15))
    timeline = []
    for e in evs:
        item = db.get(Item, e.item_id)
        txt = f"{'Correct' if e.correct else 'Missed'}: {item.stem}" + (f" ({e.hints_used} hint{'s' if e.hints_used != 1 else ''})" if e.hints_used else "")
        timeline.append({"at": e.occurred_at.isoformat(), "text": txt, "context": e.context})
    ivs = []
    for iv in db.scalars(select(Intervention).where(Intervention.student_id == student_id).order_by(Intervention.started_at.desc()).limit(8)):
        ivs.append({"concept": db.get(Concept, iv.concept_id).title, "before": round(iv.pre_p, 2), "after": round(iv.post_p, 2) if iv.post_p is not None else None, "status": iv.status,
                    "startedAt": iv.started_at.isoformat()})
    return {"id": str(s.id), "nickname": s.nickname or s.display_name, "name": s.display_name, "avatar": s.avatar, "grade": s.grade, "concepts": concepts,
            "timeline": timeline, "interventions": ivs, "levels": levels(db, student_id), "activity": learning_activity(db, student_id), "mistakes": home.mistakes(db, student_id, unresolved_only=True)[:8], "assignments": assign.for_student(db, student_id)}


def create_assignment(db: Session, teacher: Profile, class_id: uuid.UUID, *, kind: str, chapter: str | None, lesson_id: uuid.UUID | None,
                      concept_ids: list[str], due: datetime | None, note: str | None, suggestion_key: str | None, student_ids: list[uuid.UUID]) -> Assignment:
    c = owned(db, teacher, class_id)
    ch = db.scalar(select(Chapter).where(Chapter.slug == chapter)) if chapter else None
    if chapter and (ch is None or ch.status != "published"):
        raise TeacherError("That chapter is not published yet.")
    lesson = db.get(Lesson, lesson_id) if lesson_id else None
    if kind == "lesson" and not lesson:
        raise TeacherError("Choose a lesson.")
    if kind in ("practice", "test") and not (ch or concept_ids):
        raise TeacherError("Choose a chapter or topic.")
    if lesson and not db.scalar(select(LessonVersion.id).where(LessonVersion.lesson_id == lesson.id, LessonVersion.status == "published")):
        raise TeacherError("That lesson is not published yet.")
    for cid in concept_ids:
        if not db.get(Concept, cid):
            raise TeacherError("Unknown topic.")
    label = {"lesson": "Lesson", "practice": "Practice", "test": "Test", "revision": "Revision"}[kind]
    what = (db.scalar(select(LessonVersion.title).where(LessonVersion.lesson_id == lesson.id, LessonVersion.status == "published")) if lesson else None) or (ch.title if ch else db.get(Concept, concept_ids[0]).title)
    a = Assignment(classroom_id=c.id, kind=kind, chapter_id=ch.id if ch else (db.get(Lesson, lesson_id).chapter_id if lesson else None), lesson_id=lesson.id if lesson else None,
                   concept_ids=concept_ids, title=f"{label}: {what}", note=note, due_at=due, created_by=teacher.id, reason={"suggestion": suggestion_key} if suggestion_key else None)
    db.add(a)
    db.flush()
    members = {m.id for m in _members(db, c)}
    for sid in student_ids:
        if sid not in members:
            raise TeacherError("Student not found in this class.", 404)
        for cid in concept_ids:
            s = db.get(ConceptState, (sid, cid))
            if s and s.status != "secure":
                db.add(Intervention(student_id=sid, concept_id=cid, created_by=teacher.id, kind=kind, pre_p=s.p_known))
    if suggestion_key:
        db.merge(TeacherDecision(teacher_id=teacher.id, classroom_id=c.id, suggestion_key=suggestion_key, action="accepted", note=note))
    db.add(AuditLog(actor_id=teacher.id, action="teacher.assign", entity="assignment", entity_id=str(a.id), detail={"class": str(c.id), "kind": kind}))
    db.commit()
    return a


def decide(db: Session, teacher: Profile, class_id: uuid.UUID, key: str, action: str, note: str | None) -> None:
    c = owned(db, teacher, class_id)
    if action not in ("accepted", "dismissed"):
        raise TeacherError("Unknown action.")
    existing = db.scalar(select(TeacherDecision).where(TeacherDecision.classroom_id == c.id, TeacherDecision.suggestion_key == key))
    if existing:
        existing.action, existing.note = action, note
    else:
        db.add(TeacherDecision(teacher_id=teacher.id, classroom_id=c.id, suggestion_key=key, action=action, note=note))
    db.commit()


def set_leagues(db: Session, teacher: Profile, class_id: uuid.UUID, enabled: bool) -> dict:
    c = owned(db, teacher, class_id)
    c.leagues_enabled = enabled
    db.commit()
    return summary(db, c)
