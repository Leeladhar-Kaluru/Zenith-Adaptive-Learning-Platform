"""Student-facing endpoints: library, lessons, evidence, practice, tests, progress, revision, Home."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_profile, student_only
from app.engine import graph
from app.models import AssessmentSession, Board, Chapter, ChapterConcept, Concept, Item, LessonProgress, Profile, Subject
from app.services import assign, engage, evidence, gaps as gaps_svc, home, interactions, library, mission as mission_svc, notebook as notebook_svc, practice
from app.services import states as st_svc

router = APIRouter()


def learner(p: Profile = Depends(student_only)) -> Profile:
    if p.consent_status not in ("granted", "not_required"):
        raise HTTPException(403, "A parent, guardian or school needs to agree before you can start learning.")
    if not p.onboarding_completed:
        raise HTTPException(409, "Finish setting up your profile first.")
    return p


def _wrap(fn, *a, **k):
    try:
        return fn(*a, **k)
    except library.NotFound as e:
        raise HTTPException(404, str(e))
    except (practice.PracticeError, evidence.EvidenceError) as e:
        raise HTTPException(e.status, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


# ---- library -------------------------------------------------------------------------------------
@router.get("/library/boards")
def boards(db: Session = Depends(get_db)):
    return {"boards": [{"id": b.id, "name": b.name} for b in db.scalars(select(Board).where(Board.active.is_(True)).order_by(Board.name))],
            "subjects": [{"id": s.id, "name": s.name} for s in db.scalars(select(Subject).order_by(Subject.name))], "grades": [6, 7, 8, 9, 10]}


@router.get("/library/chapters")
def chapters(grade: Optional[int] = Query(None, ge=6, le=10), subject: Optional[str] = None, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return library.chapters(db, p, grade, subject)


@router.get("/library/chapters/{slug}")
def chapter(slug: str, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _wrap(library.chapter_detail, db, p, slug)


@router.get("/library/lessons/{lesson_id}")
def lesson(lesson_id: uuid.UUID, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return _wrap(library.lesson_payload, db, p, lesson_id)


@router.get("/library/search")
def search(q: str = Query("", max_length=80), allGrades: bool = False, grade: Optional[int] = None, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return library.search(db, p, q, grade, allGrades)


@router.get("/library/map/{slug}")
def concept_map(slug: str, p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    ch = db.scalar(select(Chapter).where(Chapter.slug == slug))
    if ch is None or ch.status != "published":
        raise HTTPException(404, "Chapter not found.")
    own = [c for (c,) in db.execute(select(ChapterConcept.concept_id).where(ChapterConcept.chapter_id == ch.id))]
    e = st_svc.edges(db)
    ids = set(own)
    for c in own:
        ids |= {a for a, _ in graph.ancestors(c, e, 2)}
    edges = [(a, b) for a, b in e if a in ids and b in ids]
    order = graph.topological_order(sorted(ids), edges)
    layer: dict[str, int] = {}
    for c in order:
        layer[c] = max([layer[a] + 1 for a, b in edges if b == c] or [0])
    top = max(layer.values() or [0]) or 1
    rows: dict[int, list[str]] = {}
    for c in order:
        rows.setdefault(layer[c], []).append(c)
    stt = st_svc.states(db, p.id, list(ids))
    nodes = []
    for c in db.scalars(select(Concept).where(Concept.id.in_(ids))):
        col = rows[layer[c.id]]
        parents = [a for a, b in edges if b == c.id]
        secure = lambda cid: st_svc.band(stt.get(cid)) == "secure"
        nodes.append({"id": c.id, "title": c.title, "grade": c.grade, "band": st_svc.band(stt.get(c.id)), "inChapter": c.id in own,
                      "mastery": round(stt.get(c.id, {}).get("p", 0.0), 3), "nextUnlock": (c.id in own) and not secure(c.id) and all(secure(a) for a in parents),
                      "x": 10 + 80 * layer[c.id] / top, "y": 12 + 76 * (col.index(c.id) + 0.5) / len(col), "lessonId": (library._lesson_for_concept(db, c.id) or {}).get("lessonId")})
    return {"chapterSlug": slug, "nodes": nodes, "edges": [[a, b] for a, b in edges]}


class ProgressIn(BaseModel):
    lessonId: uuid.UUID
    action: str = Field(pattern="^(start|complete)$")
    lastBlock: int = 0


@router.post("/progress")
def progress(body: ProgressIn, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    from datetime import timezone
    if body.action == "start":
        # Two tabs, a retry or a double effect can send "start" twice at once: the insert must be idempotent.
        from sqlalchemy.dialects.postgresql import insert
        db.execute(insert(LessonProgress).values(student_id=p.id, lesson_id=body.lessonId).on_conflict_do_nothing())
        row = db.get(LessonProgress, (p.id, body.lessonId))
        if row is not None and row.status != "completed" and body.lastBlock:
            row.last_block, row.updated_at = body.lastBlock, datetime.now(timezone.utc)
        db.commit()
        return {"ok": True}
    res = _wrap(library.complete_lesson, db, p, body.lessonId)
    xp = 0
    if res["first"]:
        from app.models import DailyActivity, XpEvent
        from app.engine.streaks import level as _lv  # noqa: F401
        day = engage._today()
        da = db.get(DailyActivity, (p.id, day)) or DailyActivity(student_id=p.id, day=day, answers=0, correct=0, lessons=0, xp=0, rest_day=False)
        db.add(da)
        da.lessons += 1
        key = f"lesson:{body.lessonId}"
        if not db.scalar(select(XpEvent.id).where(XpEvent.student_id == p.id, XpEvent.idem_key == key)):
            from app.core.config import settings
            from sqlalchemy import func
            today = db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.student_id == p.id, XpEvent.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))) or 0
            xp = max(0, min(20, settings.XP_DAILY_CAP - int(today)))
            if xp:
                db.add(XpEvent(student_id=p.id, kind="lesson", amount=xp, idem_key=key))
                da.xp += xp
    db.commit()
    new_badges = engage.check_badges(db, p.id)
    db.commit()
    return {**res, "xp": xp, "newBadges": new_badges}


# ---- evidence ------------------------------------------------------------------------------------
class EvidenceIn(BaseModel):
    itemId: uuid.UUID
    response: dict[str, Any]
    hintsUsed: int = Field(0, ge=0, le=5)
    ms: int = Field(0, ge=0, le=3_600_000)
    context: str = Field(pattern="^(learn_check|solve|test|probe)$")
    clientEventId: str = Field(min_length=8, max_length=64)
    sessionId: Optional[uuid.UUID] = None
    occurredAt: Optional[datetime] = None


def _record(db: Session, p: Profile, e: EvidenceIn) -> dict:
    res = _wrap(evidence.record, db, p.id, item_id=e.itemId, response=e.response, hints_used=e.hintsUsed, ms=e.ms, context=e.context,
                client_event_id=e.clientEventId, session_id=e.sessionId, occurred_at=e.occurredAt)
    res["newBadges"] = engage.check_badges(db, p.id)
    db.commit()
    return res


@router.post("/evidence")
def post_evidence(body: EvidenceIn, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    return _record(db, p, body)


class BatchIn(BaseModel):
    events: list[EvidenceIn] = Field(max_length=100)


@router.post("/evidence/batch")
def post_batch(body: BatchIn, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    """Offline sync: idempotent per clientEventId. Each event reports its own outcome."""
    out = []
    for e in sorted(body.events, key=lambda x: x.occurredAt or datetime.min):
        try:
            out.append({"clientEventId": e.clientEventId, "ok": True, "result": _record(db, p, e)})
        except HTTPException as ex:
            db.rollback()
            out.append({"clientEventId": e.clientEventId, "ok": False, "error": ex.detail, "status": ex.status_code})
    return {"results": out}


class InteractionIn(BaseModel):
    clientEventId: str = Field(min_length=8, max_length=64)
    kind: str = Field(max_length=16)
    targetType: str = Field(min_length=1, max_length=16)
    targetId: str = Field(min_length=1, max_length=120)
    value: dict[str, Any] = Field(default_factory=dict)
    ms: int = Field(0, ge=0, le=3_600_000)
    occurredAt: Optional[datetime] = None


class InteractionBatch(BaseModel):
    events: list[InteractionIn] = Field(max_length=interactions.MAX_PER_REQUEST)


@router.post("/interactions/batch")
def post_interactions(body: InteractionBatch, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    """Everything the student does while learning (reading time, hints, answer edits, simulation changes). Idempotent."""
    return interactions.store(db, p.id, [e.model_dump() for e in body.events])


@router.get("/items/{item_id}/hint")
def hint(item_id: uuid.UUID, n: int = Query(1, ge=1, le=5), p: Profile = Depends(learner), db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None or item.status not in ("published", "generated"):
        raise HTTPException(404, "Question not found.")
    hs = item.hints or []
    if not hs:
        raise HTTPException(404, "This question has no hints.")
    return {"n": min(n, len(hs)), "of": len(hs), "hint": hs[min(n, len(hs)) - 1]}


# ---- practice and tests -------------------------------------------------------------------------
@router.get("/practice/next")
def practice_next(chapter: Optional[str] = None, concept: Optional[str] = None, weak: bool = False, review: bool = False, harder: bool = False, pattern: Optional[str] = None,
                  p: Profile = Depends(learner), db: Session = Depends(get_db)):
    return _wrap(practice.next_item, db, p, chapter=chapter, concept=concept, weak=weak, review=review, harder=harder, pattern=pattern)


class AssessIn(BaseModel):
    kind: str
    chapter: Optional[str] = None
    concept: Optional[str] = None
    timed: bool = False
    assignmentId: Optional[uuid.UUID] = None


@router.post("/assessments")
def create_assessment(body: AssessIn, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    s = _wrap(practice.create_assessment, db, p, body.kind, chapter=body.chapter, concept=body.concept, timed=body.timed, assignment_id=body.assignmentId)
    return practice.session_view(db, s)


def _own_session(db: Session, p: Profile, sid: uuid.UUID) -> AssessmentSession:
    s = db.get(AssessmentSession, sid)
    if s is None or s.student_id != p.id:
        raise HTTPException(404, "Test not found.")
    return s


@router.get("/assessments")
def list_assessments(p: Profile = Depends(learner), db: Session = Depends(get_db)):
    rows = db.scalars(select(AssessmentSession).where(AssessmentSession.student_id == p.id, AssessmentSession.status == "submitted").order_by(AssessmentSession.submitted_at.desc()).limit(20))
    return [{"id": str(s.id), "kind": s.kind, "submittedAt": s.submitted_at.isoformat(), "right": (s.summary or {}).get("right"), "total": (s.summary or {}).get("total")} for s in rows]


@router.get("/assessments/{sid}")
def get_assessment(sid: uuid.UUID, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    return practice.session_view(db, _own_session(db, p, sid))


@router.post("/assessments/{sid}/submit")
def submit_assessment(sid: uuid.UUID, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    return _wrap(practice.submit, db, p, _own_session(db, p, sid))


# ---- Home, progress, revision, engagement -------------------------------------------------------
@router.get("/stats")
def stats(p: Profile = Depends(learner), db: Session = Depends(get_db)):
    """The few numbers the header shows (XP level, streak, today's XP). Light enough to refresh after every answer."""
    return home.stats(db, p)


@router.get("/mission")
def daily_mission(p: Profile = Depends(learner), db: Session = Depends(get_db)):
    """Up to three short steps for today (revise, learn, stretch), each with its reason; at most 12 minutes."""
    return mission_svc.mission(db, p)


@router.get("/today")
def today(p: Profile = Depends(learner), db: Session = Depends(get_db)):
    return home.today(db, p)


@router.get("/progress/overview")
def overview(p: Profile = Depends(learner), db: Session = Depends(get_db)):
    return home.overview(db, p)


@router.get("/progress/gaps")
def progress_gaps(p: Profile = Depends(learner), db: Session = Depends(get_db)):
    """Where the student is lacking: ranked gaps with confidence ranges, root causes, a repair order, and the lesson, practice and test for each."""
    return gaps_svc.gap_map(db, p)


@router.get("/progress/notebook")
def notebook(resolved: bool = False, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    """Wrong answers grouped by the misunderstanding behind them, with a way to practise each."""
    return notebook_svc.notebook(db, p.id, include_resolved=resolved)


@router.get("/boss/{chapter}")
def boss_status(chapter: str, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    """Whether the chapter boss quiz is open yet, and what is still needed."""
    return _wrap(practice.boss_status, db, p, chapter)


@router.get("/progress/mistakes")
def mistakes(all: bool = False, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    return home.mistakes(db, p.id, unresolved_only=not all)


@router.get("/revision")
def revision(p: Profile = Depends(learner), db: Session = Depends(get_db)):
    return home.revision_view(db, p)


class CardIn(BaseModel):
    remembered: bool


@router.post("/revision/cards/{card_id}/review")
def review_card(card_id: uuid.UUID, body: CardIn, p: Profile = Depends(learner), db: Session = Depends(get_db)):
    try:
        return home.review_card(db, p, card_id, body.remembered)
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.get("/gamification")
def gamification(p: Profile = Depends(learner), db: Session = Depends(get_db)):
    lg = engage.league_view(db, p)
    db.commit()
    return {**lg, "quests": engage.quests(db, p.id), "badges": engage.badge_catalog(db, p.id), "streak": engage.streak_info(db, p.id),
            "xp": engage.streaks.level(engage.total_xp(db, p.id))}


@router.get("/assignments")
def my_assignments(p: Profile = Depends(learner), db: Session = Depends(get_db)):
    return assign.for_student(db, p.id)


@router.get("/explore")
def explore(p: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    """What a student can really do today: flashcards, and every simulation, chart or map found in a published lesson."""
    from app.services import explore as explore_svc
    return {"available": explore_svc.available(db), "labs": explore_svc.labs(db, p.grade)}