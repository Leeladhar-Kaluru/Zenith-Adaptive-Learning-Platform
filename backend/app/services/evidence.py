"""Record one answer: grade it, update the learner model, award honest XP, schedule revision."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.engine import bkt, elo, grading, ladder, signals
from app.models import (AssessmentSession, Concept, ConceptLevel, ConceptState, InteractionEvent, DailyActivity, EvidenceEvent, Intervention, Item, LearnerRating,
                        RevisionSchedule, XpEvent)
from app.services import items as item_svc

INTERVALS = [1, 3, 7, 21, 45]
XP_BASE = {"intro": 5, "standard": 10, "challenge": 15}
STATE_RANK = {"unassessed": 0, "gap_confirmed": 1, "gap_suspected": 1, "learning": 2, "secure": 3}


class EvidenceError(ValueError):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def result_from_event(db: Session, ev: EvidenceEvent, item: Item) -> dict:
    g = grading.grade(item.kind, item.answer_spec, ev.response)
    mis = db.get(item_svc.Misconception, ev.misconception_id) if ev.misconception_id else None
    xp = db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.student_id == ev.student_id, XpEvent.idem_key == f"answer:{ev.id}"))
    concepts = []
    for c in ev.concepts:
        st = db.get(ConceptState, (ev.student_id, c["id"]))
        concepts.append({**c, "status": st.status if st else "unassessed", "n_obs": st.n_obs if st else 0})
    return _result(db, item, g, concepts, mis, int(xp or 0), ev.hints_used, changed=[])


def _result(db: Session, item: Item, g: grading.Grade, concepts: list[dict], mis, xp: int, hints: int, changed: list[dict]) -> dict:
    titles = {c.id: c.title for c in db.scalars(select(Concept).where(Concept.id.in_([c["id"] for c in concepts])))} if concepts else {}
    feedback = item.explanation if g.correct else (
        (f"Common mistake: {mis.description} " if mis else "") + item.explanation)
    return {"correct": g.correct, "score": g.score, "reveal": g.reveal, "feedback": feedback.strip(),
            "misconception": mis.description if mis else None, "xp": xp,
            "concepts": [{"id": c["id"], "title": titles.get(c["id"], c["id"]), "band": c["status"], "pKnown": round(c["p_after"], 3),
                          "evidence": c["n_obs"], "confidence": bkt.uncertainty(c["n_obs"])} for c in concepts],
            "changes": changed}


def record(db: Session, student_id: uuid.UUID, *, item_id: uuid.UUID, response: dict, hints_used: int, ms: int, context: str,
           client_event_id: str, session_id: uuid.UUID | None = None, occurred_at: datetime | None = None, confidence: int | None = None) -> dict:
    item = db.get(Item, item_id)
    if item is None or item.status not in ("published", "generated"):
        raise EvidenceError("That question is not available.", 404)

    existing = db.scalar(select(EvidenceEvent).where(EvidenceEvent.student_id == student_id, EvidenceEvent.client_event_id == client_event_id))
    if existing:
        return {**result_from_event(db, existing, item), "alreadyRecorded": True}

    session = None
    if session_id:
        session = db.get(AssessmentSession, session_id)
        if session is None or session.student_id != student_id:
            raise EvidenceError("That test was not found.", 404)
        if session.status != "active":
            raise EvidenceError("This test has already been submitted.", 409)
        if str(item_id) not in session.item_ids:
            raise EvidenceError("That question is not part of this test.", 422)
        if session.time_limit_s and (_now() - session.started_at).total_seconds() > session.time_limit_s + 15:
            raise EvidenceError("Time is up for this test.", 409)
        if db.scalar(select(func.count(EvidenceEvent.id)).where(EvidenceEvent.session_id == session_id, EvidenceEvent.item_id == item_id,
                                                                EvidenceEvent.student_id == student_id)):
            raise EvidenceError("You already answered this question in this test.", 409)

    try:
        g = grading.grade(item.kind, item.answer_spec, response)
    except (KeyError, ValueError, TypeError):
        raise EvidenceError("That answer is not in the expected format.")

    now = _now()
    links = item_svc.item_concepts(db, item.id)
    n_options = len((item.payload or {}).get("options", [])) or 4
    attempt_no = (db.scalar(select(func.count(EvidenceEvent.id)).where(EvidenceEvent.student_id == student_id, EvidenceEvent.item_id == item.id)) or 0) + 1
    hints = max(0, min(hints_used, len(item.hints or [])))

    concept_rows, changed = [], []
    subject_id = None
    for cid, w in links:
        concept = db.get(Concept, cid)
        subject_id = subject_id or concept.subject_id
        st = db.get(ConceptState, (student_id, cid))
        if st is None:
            st = ConceptState(student_id=student_id, concept_id=cid, p_known=bkt.P_INIT, n_obs=0, n_correct=0, streak=0,
                              status="unassessed", param_version=bkt.PARAM_VERSION)
            db.add(st)
            db.flush()
        before_p, before_status, before_level = st.p_known, st.status, bkt.level(st.p_known, st.n_obs)
        # Getting the same question right again is memory, not new understanding: it barely moves the estimate
        # and is not counted as a new observation. Missing it again is real evidence and counts in full.
        repeat_right = g.correct and attempt_no > 1
        repeat_discount = 0.1 if repeat_right else 1.0
        st.p_known = bkt.update(st.p_known, correct=g.correct, kind=item.kind, n_options=n_options, difficulty=item.difficulty,
                                hints_used=hints, weight=w * repeat_discount)
        if not repeat_right:
            st.n_obs += 1
            st.n_correct += 1 if g.correct else 0
            st.streak = st.streak + 1 if g.correct else 0
        st.status = bkt.status(st.p_known, st.n_obs, st.n_correct)
        st.last_obs_at, st.param_version, st.updated_at = now, bkt.PARAM_VERSION, now
        concept_rows.append({"id": cid, "w": w, "p_before": before_p, "p_after": st.p_known, "status": st.status, "n_obs": st.n_obs})
        if STATE_RANK[st.status] > STATE_RANK[before_status] or bkt.level(st.p_known, st.n_obs) > before_level:
            changed.append({"concept": cid, "title": concept.title, "from": before_status, "to": st.status, "level": bkt.level(st.p_known, st.n_obs)})
        _schedule_revision(db, student_id, cid, st.status, g.correct, now)
        _close_interventions(db, student_id, cid, st, now)

    # Rasch rating
    if subject_id:
        lr = db.get(LearnerRating, (student_id, subject_id))
        if lr is None:
            lr = LearnerRating(student_id=student_id, subject_id=subject_id, theta=0.0, n=0)
            db.add(lr)
            db.flush()
        lr.theta, item.beta = elo.update(lr.theta, item.beta, g.correct, lr.n, item.n_obs)
        lr.n += 1
        item.n_obs += 1

    mis = item_svc.misconception_for(db, item, g.selected) if not g.correct else None
    ev = EvidenceEvent(student_id=student_id, item_id=item.id, session_id=session_id, client_event_id=client_event_id, context=context,
                       response=response, correct=g.correct, score=g.score, hints_used=hints, ms=max(0, ms), attempt_no=attempt_no, confidence=confidence if confidence in (1, 2, 3) else None,
                       concepts=[{k: v for k, v in c.items() if k != "status"} for c in concept_rows],
                       misconception_id=mis.id if mis else None, param_version=bkt.PARAM_VERSION, occurred_at=occurred_at or now)
    db.add(ev)
    db.flush()
    level_change = _move_ladder(db, student_id, item, links, g.correct, hints, max(0, ms), now)

    xp = _award_xp(db, student_id, ev, item, g.correct, hints, attempt_no, changed, now)
    _daily(db, student_id, now.date(), g.correct, xp)
    db.commit()
    return {**_result(db, item, g, concept_rows, mis, xp, hints, changed), "levelChange": level_change, "alreadyRecorded": False}


# ---- helpers -----------------------------------------------------------------------------------
def _median_ms(db: Session, student_id, concept_id: str) -> float:
    """The student's own typical time on correct answers for this concept (0 until there are enough to judge)."""
    rows = [ms for (ms,) in db.execute(select(EvidenceEvent.ms).where(EvidenceEvent.student_id == student_id, EvidenceEvent.correct.is_(True),
                                                                      EvidenceEvent.ms > 0, EvidenceEvent.concepts.contains([{"id": concept_id}]))
                                       .order_by(EvidenceEvent.occurred_at.desc()).limit(30))]
    if len(rows) < 5:
        return 0.0
    rows.sort()
    return float(rows[len(rows) // 2])


def _move_ladder(db: Session, student_id, item: Item, links, correct: bool, hints: int, ms: int, now: datetime) -> dict | None:
    """Move this student up or down the 1-5 ladder for the item's main concept, using hints, edits and speed as well as correctness."""
    if not links:
        return None
    concept_id = max(links, key=lambda cw: cw[1])[0]
    row = db.get(ConceptLevel, (student_id, concept_id))
    start = item.level if item.level else 1
    if row is None:
        row = ConceptLevel(student_id=student_id, concept_id=concept_id, level=start, streak_up=0, streak_down=0, reason="")
        db.add(row)
    since = now - timedelta(minutes=15)
    events = [{"kind": k} for (k,) in db.execute(select(InteractionEvent.kind).where(
        InteractionEvent.student_id == student_id, InteractionEvent.target_id == str(item.id), InteractionEvent.occurred_at >= since))]
    sig = signals.classify(events, ms, correct, _median_ms(db, student_id, concept_id))
    before = row.level or start
    lvl, up, down, why = ladder.step(before, row.streak_up or 0, row.streak_down or 0, correct=correct, hints_used=hints,
                                     fluent=sig["fluent"], struggling=sig["struggling"], guessing=sig["guessing"])
    row.level, row.streak_up, row.streak_down, row.reason, row.updated_at = lvl, up, down, why, now
    return {"concept": concept_id, "from": before, "to": lvl, "reason": why, "signal": sig["reason"]} if lvl != before else None


def _schedule_revision(db: Session, student_id, concept_id: str, status: str, correct: bool, now: datetime):
    row = db.get(RevisionSchedule, (student_id, concept_id))
    if status == "secure" and correct:
        reps = (row.reps + 1) if row else 0
        days = INTERVALS[min(reps, len(INTERVALS) - 1)]
        due = now + timedelta(days=days)
        if row:
            row.reps, row.interval_days, row.due_at, row.last_reviewed_at = reps, days, due, now
        else:
            db.add(RevisionSchedule(student_id=student_id, concept_id=concept_id, due_at=due, interval_days=days, reps=0, last_reviewed_at=now))
    elif row and not correct:
        row.reps, row.interval_days, row.due_at, row.last_reviewed_at = 0, 1, now + timedelta(days=1), now


def _close_interventions(db: Session, student_id, concept_id: str, st: ConceptState, now: datetime):
    if st.status not in ("secure", "learning"):
        return
    for iv in db.scalars(select(Intervention).where(Intervention.student_id == student_id, Intervention.concept_id == concept_id, Intervention.status == "open")):
        if st.p_known - iv.pre_p >= 0.25 or st.status == "secure":
            iv.post_p, iv.status, iv.closed_at = st.p_known, "closed", now


def _daily(db: Session, student_id, day: date, correct: bool, xp: int):
    row = db.get(DailyActivity, (student_id, day))
    if row is None:
        row = DailyActivity(student_id=student_id, day=day, answers=0, correct=0, lessons=0, xp=0, rest_day=False)
        db.add(row)
    row.answers += 1
    row.correct += 1 if correct else 0
    row.xp += xp


def _award_xp(db: Session, student_id, ev: EvidenceEvent, item: Item, correct: bool, hints: int, attempt_no: int, changed: list[dict], now: datetime) -> int:
    """XP rewards learning, not clicking: first-try correct answers on questions not seen recently, plus a bonus when a concept becomes secure."""
    day_total = db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.student_id == student_id,
                                                                                   XpEvent.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0))) or 0
    room = max(0, settings.XP_DAILY_CAP - int(day_total))
    total = 0

    def grant(kind: str, amount: int, key: str):
        nonlocal total, room
        amt = min(amount, room)
        if amt <= 0:
            return
        if db.scalar(select(XpEvent.id).where(XpEvent.student_id == student_id, XpEvent.idem_key == key)):
            return
        db.add(XpEvent(student_id=student_id, kind=kind, amount=amt, idem_key=key))
        total += amt
        room -= amt

    if correct:
        seen_recently = db.scalar(select(func.count(EvidenceEvent.id)).where(
            EvidenceEvent.student_id == student_id, EvidenceEvent.item_id == item.id, EvidenceEvent.id != ev.id,
            EvidenceEvent.occurred_at >= now - timedelta(days=7))) or 0
        if attempt_no == 1 and not seen_recently:
            base = XP_BASE.get(item.difficulty, 10)
            grant("answer", base if hints == 0 else max(1, round(base * 0.4)), f"answer:{ev.id}")
    for ch in changed:
        if ch["to"] == "secure" and ch["from"] != "secure":
            grant("mastery", 25, f"mastery:{ch['concept']}")
    return total
