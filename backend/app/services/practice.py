"""Adaptive practice and assessments built on the learner model."""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.engine import bkt, graph, selector
from app.engine.templates import templates_for
from app.models import (AssessmentSession, Chapter, ChapterConcept, Concept, EvidenceEvent, Item, ItemConcept, Lesson, LessonVersion,
                        LessonVersionItem, Misconception, Profile, RevisionSchedule)
from app.services import generator
from app.services import items as item_svc
from app.services import library
from app.services import states as st_svc


GENERATED_SHARE = 0.7


class PracticeError(ValueError):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def _now():
    return datetime.now(timezone.utc)


def pool(db: Session, concept_ids: list[str], purposes: tuple[str, ...] = ("check", "practice", "test", "probe"), grade_max: int | None = None) -> list[dict]:
    """Published items (belonging to a published lesson version) that assess any of the concepts."""
    rows = db.execute(
        select(Item, ItemConcept.concept_id, ItemConcept.weight)
        .join(ItemConcept, ItemConcept.item_id == Item.id)
        .join(LessonVersionItem, LessonVersionItem.item_id == Item.id)
        .join(LessonVersion, and_(LessonVersion.id == LessonVersionItem.lesson_version_id, LessonVersion.status == "published"))
        .where(Item.status == "published", Item.purpose.in_(purposes)).distinct()).all()
    by: dict[uuid.UUID, dict] = {}
    for item, cid, w in rows:
        d = by.setdefault(item.id, {"id": str(item.id), "obj": item, "difficulty": item.difficulty, "beta": item.beta, "concepts": []})
        d["concepts"].append((cid, w))
    wanted = set(concept_ids)
    return [d for d in by.values() if any(c in wanted for c, _ in d["concepts"])]


def _recent(db: Session, student_id, days: float = 2) -> set[str]:
    since = _now() - timedelta(days=days)
    return {str(i) for (i,) in db.execute(select(EvidenceEvent.item_id).where(EvidenceEvent.student_id == student_id, EvidenceEvent.occurred_at >= since))}


def scope_concepts(db: Session, profile: Profile, chapter: str | None, concept: str | None, weak: bool, review: bool) -> tuple[list[str], str]:
    stt = st_svc.states(db, profile.id)
    if concept:
        if not db.get(Concept, concept):
            raise PracticeError("Unknown topic.", 404)
        return [concept], "topic"
    if chapter:
        ch = db.scalar(select(Chapter).where(Chapter.slug == chapter))
        if ch is None or ch.status != "published":
            raise PracticeError("That chapter is not available yet.", 404)
        return [c for (c,) in db.execute(select(ChapterConcept.concept_id).where(ChapterConcept.chapter_id == ch.id))], "chapter"
    if review:
        due = [c for (c,) in db.execute(select(RevisionSchedule.concept_id).where(RevisionSchedule.student_id == profile.id, RevisionSchedule.due_at <= _now()))]
        if not due:
            raise PracticeError("Nothing is due for revision right now.", 409)
        return due, "revision"
    if weak:
        ids = [c for c, s in stt.items() if s["status"] in ("gap_suspected", "gap_confirmed", "learning") and s["p"] < 0.8]
        if not ids:
            raise PracticeError("No weak topics found yet. Answer a few questions and ZENITH will find them.", 409)
        return ids, "weak"
    # default: concepts of published chapters for the student's class
    ids = [c for (c,) in db.execute(select(ChapterConcept.concept_id).join(Chapter, Chapter.id == ChapterConcept.chapter_id)
                                    .where(Chapter.status == "published", Chapter.grade == profile.grade))]
    return ids, "class"


def next_item(db: Session, profile: Profile, *, chapter=None, concept=None, weak=False, review=False, harder=False) -> dict:
    ids, scope = scope_concepts(db, profile, chapter, concept, weak, review)
    cands = pool(db, ids, ("check", "practice", "probe", "test"))
    stt = st_svc.states(db, profile.id)
    rng = random.Random()
    # Concepts with question templates get a fresh question at the student's own level most of the time.
    if any(templates_for(c) for c in ids) and (not cands or rng.random() < GENERATED_SHARE):
        got = generator.next_generated(db, profile, ids, stt, harder=harder, recent=_recent(db, profile.id), rng=rng)
        if got:
            item, level, reason = got
            db.commit()
            primary = max(item_svc.item_concepts(db, item.id), key=lambda cw: cw[1])[0]
            st = stt.get(primary)
            return {"item": item_svc.public_item(item), "scope": scope, "generated": True,
                    "concept": {"id": primary, "title": db.get(Concept, primary).title, "level": level, "band": st_svc.band(st)},
                    "why": reason or f"A fresh question at level {level} of 5, matched to how you are doing.", "ladderLevel": level}
    if not cands:
        raise PracticeError("No questions are available for this yet. A teacher is still reviewing them.", 409)
    c0 = db.get(Concept, ids[0])
    theta = st_svc.theta(db, profile.id, c0.subject_id)
    mode = "challenge" if harder else ("repair" if scope == "weak" else "practice")
    pick = selector.choose_item(cands, theta, stt, _recent(db, profile.id), mode, rng)
    item = pick["obj"]
    primary = max(pick["concepts"], key=lambda cw: cw[1])[0]
    st = stt.get(primary)
    lvl = bkt.level(st["p"], st["n"]) if st else 1
    return {"item": item_svc.public_item(item), "scope": scope,
            "concept": {"id": primary, "title": db.get(Concept, primary).title, "level": lvl, "band": st_svc.band(st)},
            "why": _why(scope, st, item.difficulty)}


def _why(scope: str, st: dict | None, difficulty: str) -> str:
    if not st or st["n"] < 3:
        return "A first question to see where you are."
    if difficulty == "challenge":
        return "You are doing well here, so this one is harder."
    if scope == "weak" or st["p"] < 0.45:
        return "A step-by-step question to strengthen this topic."
    return "Matched to what you can do right now."


def unlocks(db: Session, profile: Profile) -> dict:
    """What opens up next: lessons whose prerequisites are secure, and enrichment topics for strong concepts."""
    stt = st_svc.states(db, profile.id)
    e = st_svc.edges(db)
    secure = {c for c, s in stt.items() if s["status"] == "secure"}
    parents: dict[str, list[str]] = {}
    for a, b in e:
        parents.setdefault(b, []).append(a)
    enrich = []
    for c in db.scalars(select(Concept).where(Concept.enrichment.is_(True))):
        pre = parents.get(c.id, [])
        if pre and all(p in secure for p in pre):
            les = library._lesson_for_concept(db, c.id)
            if les:
                enrich.append({"conceptId": c.id, "title": c.title, "lessonId": les["lessonId"]})
    return {"enrichment": enrich}


# ---- assessments -------------------------------------------------------------------------------
KINDS = ("diagnostic", "chapter_test", "topic_test", "revision")


def create_assessment(db: Session, profile: Profile, kind: str, *, chapter: str | None = None, concept: str | None = None, timed: bool = False,
                      assignment_id: uuid.UUID | None = None) -> AssessmentSession:
    if kind not in KINDS:
        raise PracticeError("Unknown test type.")
    e = st_svc.edges(db)
    ch = None
    if kind in ("diagnostic", "chapter_test"):
        if not chapter:
            raise PracticeError("Choose a chapter.")
        ch = db.scalar(select(Chapter).where(Chapter.slug == chapter))
        if ch is None or ch.status != "published":
            raise PracticeError("That chapter is not available yet.", 404)
        cids = [c for (c,) in db.execute(select(ChapterConcept.concept_id).where(ChapterConcept.chapter_id == ch.id))]
        if kind == "diagnostic":
            extra = {a for c in cids for a, d in graph.ancestors(c, e, 2)}
            order = graph.topological_order([c for (c,) in db.execute(select(Concept.id))], e)
            cids = sorted(set(cids) | extra, key=order.index)
    elif kind == "topic_test":
        if not concept or not db.get(Concept, concept):
            raise PracticeError("Choose a topic.")
        cids = [concept]
    else:
        due = [c for (c,) in db.execute(select(RevisionSchedule.concept_id).where(RevisionSchedule.student_id == profile.id, RevisionSchedule.due_at <= _now()))]
        if not due:
            raise PracticeError("Nothing is due for revision right now.", 409)
        cids = due[:8]

    purposes = ("probe", "practice", "check", "test") if kind == "diagnostic" else ("test", "practice")
    cands = pool(db, cids, purposes)
    if not cands:
        raise PracticeError("No questions are available for this yet.", 409)
    stt = st_svc.states(db, profile.id)
    theta = st_svc.theta(db, profile.id, db.get(Concept, cids[0]).subject_id)
    rng = random.Random()
    chosen: list[dict] = []
    limit = {"diagnostic": 10, "chapter_test": 10, "topic_test": 6, "revision": 8}[kind]
    per_concept = 2 if kind == "diagnostic" else 1
    for cid in cids:  # coverage first: best item per concept
        for _ in range(per_concept):
            sub = [c for c in cands if any(x == cid for x, _ in c["concepts"]) and c not in chosen]
            pick = selector.choose_item(sub, theta, stt, set(), "test", rng) if sub else None
            if pick:
                chosen.append(pick)
            if len(chosen) >= limit:
                break
        if len(chosen) >= limit:
            break
    while len(chosen) < min(limit, len(cands)):
        rest = [c for c in cands if c not in chosen]
        pick = selector.choose_item(rest, theta, stt, set(), "test", rng)
        if not pick:
            break
        chosen.append(pick)
    chosen.sort(key=lambda c: {"intro": 0, "standard": 1, "challenge": 2}[c["difficulty"]])
    s = AssessmentSession(student_id=profile.id, kind=kind, chapter_id=ch.id if ch else None, assignment_id=assignment_id,
                          concept_ids=cids, item_ids=[c["id"] for c in chosen], time_limit_s=(len(chosen) * 90 if timed else None))
    db.add(s)
    db.commit()
    return s


def session_view(db: Session, s: AssessmentSession) -> dict:
    ch = db.get(Chapter, s.chapter_id) if s.chapter_id else None
    base = {"id": str(s.id), "kind": s.kind, "status": s.status, "timeLimitS": s.time_limit_s, "startedAt": s.started_at.isoformat(), "total": len(s.item_ids),
            "chapter": ch.slug if ch else None, "conceptId": (s.concept_ids[0] if s.kind == "topic_test" and s.concept_ids else None)}
    if s.status == "active":
        items = {str(i.id): i for i in db.scalars(select(Item).where(Item.id.in_([uuid.UUID(x) for x in s.item_ids])))}
        answered = {str(i) for (i,) in db.execute(select(EvidenceEvent.item_id).where(EvidenceEvent.session_id == s.id))}
        remaining = None
        if s.time_limit_s:
            remaining = max(0, int(s.time_limit_s - (_now() - s.started_at).total_seconds()))
        return {**base, "items": [item_svc.public_item(items[i]) for i in s.item_ids], "answered": sorted(answered), "remainingS": remaining}
    return {**base, "summary": s.summary}


def submit(db: Session, profile: Profile, s: AssessmentSession) -> dict:
    if s.student_id != profile.id:
        raise PracticeError("Not your test.", 404)
    if s.status == "submitted":
        return session_view(db, s)
    evs = list(db.scalars(select(EvidenceEvent).where(EvidenceEvent.session_id == s.id)))
    by_item = {str(e.item_id): e for e in evs}
    total = len(s.item_ids)
    right = sum(1 for e in evs if e.correct)
    per: dict[str, dict] = {}
    mistakes = []
    for iid in s.item_ids:
        item = db.get(Item, uuid.UUID(iid))
        ev = by_item.get(iid)
        cids = [c for c, _ in item_svc.item_concepts(db, item.id)]
        for c in cids:
            d = per.setdefault(c, {"right": 0, "total": 0})
            d["total"] += 1
            d["right"] += 1 if (ev and ev.correct) else 0
        if ev is None or not ev.correct:
            mis = db.get(Misconception, ev.misconception_id) if ev and ev.misconception_id else None
            mistakes.append({"itemId": iid, "stem": item.stem, "answered": ev is not None, "explanation": item.explanation,
                             "misconception": mis.description if mis else None, "concepts": cids})
    stt = st_svc.states(db, profile.id)
    e = st_svc.edges(db)
    by_concept, suggestions = [], []
    for c, d in per.items():
        con = db.get(Concept, c)
        st = stt.get(c)
        acc = d["right"] / d["total"]
        by_concept.append({"conceptId": c, "title": con.title, "right": d["right"], "total": d["total"], "band": st_svc.band(st),
                           "evidence": st["n"] if st else 0, "confidence": bkt.uncertainty(st["n"] if st else 0)})
        if acc < 0.6:
            les = library._lesson_for_concept(db, c)
            root = graph.investigate(c, e, stt)["root"]
            suggestions.append({"conceptId": c, "title": con.title,
                                "action": "prerequisite" if root else "lesson" if les else "practice",
                                "why": f"You got {d['right']} of {d['total']} right on this topic.",
                                "href": f"/lesson/{library._lesson_for_concept(db, root)['lessonId']}" if root and library._lesson_for_concept(db, root)
                                else (f"/lesson/{les['lessonId']}" if les else f"/practice?concept={c}")})
    summary = {"right": right, "total": total, "answered": len(evs), "accuracy": round(right / total, 3) if total else 0,
               "byConcept": by_concept, "mistakes": mistakes, "suggestions": suggestions,
               "note": "A test score is one signal. The concept bands show what you understand, and how sure we are."}
    s.status, s.submitted_at, s.summary = "submitted", _now(), summary
    db.commit()
    return session_view(db, s)
