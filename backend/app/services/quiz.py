"""1v1 class quiz. Two students of the SAME class, close in learner rating, answer the same five published questions; the server grades every answer.

No background process: matchmaking and the clock are resolved when a player asks for the state, so it works as serverless functions. Questions are
checked by the deterministic grader, never by a model. Quiz Elo is kept apart from the learner model: a quiz cannot change mastery. Only a nickname
and avatar are shown to the opponent, and students who opted out of competitive features (or classes with leagues off) are never matched."""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.engine import grading
from app.models import Chapter, ChapterConcept, ClassMember, Classroom, Item, Profile, QuizAnswer, QuizMatch, QuizPlayer, QuizRating
from app.services import items as item_svc
from app.services import practice, states
from app.services.classes import ClassError, access

QUESTIONS = 5
KINDS = ("mcq", "truefalse", "numeric")
MATCH_MINUTES = 6
WAIT_SECONDS = 120
BASE_WINDOW = 0.5                 # learner-rating gap allowed at first; widens by 0.25 every 20 s of waiting so nobody waits forever
K = 24


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _check_allowed(db: Session, p: Profile, c: Classroom) -> None:
    if p.role != "student":
        raise ClassError("Only students play quizzes.", 403)
    if p.consent_status not in ("granted", "not_required"):
        raise ClassError("A parent, guardian or school needs to agree first.", 403)
    if p.league_opt_out:
        raise ClassError("You turned off competitive features in your settings.", 403)
    if not c.leagues_enabled:
        raise ClassError("Your teacher has turned off competitive features for this class.", 403)


def rating(db: Session, student_id: uuid.UUID) -> QuizRating:
    r = db.get(QuizRating, student_id)
    if r is None:
        r = QuizRating(student_id=student_id, rating=1000.0, games=0)
        db.add(r)
        db.flush()
    return r


def _mine(db: Session, p: Profile, c: Classroom) -> QuizMatch | None:
    return db.scalar(select(QuizMatch).join(QuizPlayer, QuizPlayer.match_id == QuizMatch.id)
                     .where(QuizPlayer.student_id == p.id, QuizMatch.classroom_id == c.id, QuizMatch.status.in_(("waiting", "active"))).limit(1))


def _pick(db: Session, c: Classroom, mean_theta: float, seed: str) -> list[Item]:
    cids = [x for (x,) in db.execute(select(ChapterConcept.concept_id).join(Chapter, Chapter.id == ChapterConcept.chapter_id)
                                     .where(Chapter.status == "published", Chapter.grade == c.grade, Chapter.subject_id == c.subject_id))]
    pool = [d for d in practice.pool(db, cids, ("check", "practice", "test")) if d["obj"].kind in KINDS and not (d["obj"].payload or {}).get("svg")]
    if len(pool) < QUESTIONS:
        raise ClassError("Not enough questions for a quiz in this class yet.", 409)
    pool.sort(key=lambda d: (abs(d["beta"] - mean_theta), d["id"]))
    near = pool[: QUESTIONS * 3]                              # the 15 closest to the pair's level; five are drawn from them with a recorded seed
    chosen = random.Random(seed).sample(near, QUESTIONS)
    return sorted((d["obj"] for d in chosen), key=lambda i: i.beta)


def join(db: Session, p: Profile, class_id: uuid.UUID) -> dict:
    """Find an opponent in this class, or wait for one. Calling again while already queued or playing just returns that match."""
    c = access(db, p, class_id)
    _check_allowed(db, p, c)
    mine = _mine(db, p, c)
    if mine is not None:
        return state(db, p, mine.id)
    theta = states.theta(db, p.id, c.subject_id)
    now = _now()
    for m in db.scalars(select(QuizMatch).where(QuizMatch.classroom_id == c.id, QuizMatch.status == "waiting").order_by(QuizMatch.created_at)):
        if now - m.created_at > timedelta(seconds=WAIT_SECONDS):
            m.status, m.ended_at = "cancelled", now
            continue
        host = db.scalars(select(QuizPlayer).where(QuizPlayer.match_id == m.id)).first()
        waited = (now - m.created_at).total_seconds()
        if host is None or host.student_id == p.id or abs(host.theta - theta) > BASE_WINDOW + 0.25 * (waited // 20):
            continue
        seed = str(m.id)
        items = _pick(db, c, (host.theta + theta) / 2, seed)
        m.item_ids = [str(i.id) for i in items]
        m.detail = {"seed": seed, "targetTheta": round((host.theta + theta) / 2, 3), "window": BASE_WINDOW + 0.25 * (waited // 20)}
        m.status, m.started_at, m.deadline_at = "active", now, now + timedelta(minutes=MATCH_MINUTES)
        db.add(QuizPlayer(match_id=m.id, student_id=p.id, theta=theta))
        db.commit()
        return state(db, p, m.id)
    m = QuizMatch(classroom_id=c.id, status="waiting")
    db.add(m)
    db.flush()
    db.add(QuizPlayer(match_id=m.id, student_id=p.id, theta=theta))
    db.commit()
    return state(db, p, m.id)


def _players(db: Session, m: QuizMatch) -> list[QuizPlayer]:
    return list(db.scalars(select(QuizPlayer).where(QuizPlayer.match_id == m.id).order_by(QuizPlayer.joined_at)))


def _match(db: Session, p: Profile, match_id: uuid.UUID) -> tuple[QuizMatch, QuizPlayer]:
    m = db.get(QuizMatch, match_id)
    me = db.get(QuizPlayer, (match_id, p.id)) if m else None
    if m is None or me is None:
        raise ClassError("Quiz not found.", 404)
    return m, me


def _expected(a: float, b: float) -> float:
    return 1 / (1 + 10 ** ((b - a) / 400))


def _finish(db: Session, m: QuizMatch) -> None:
    ps = _players(db, m)
    m.status, m.ended_at = "done", _now()
    if len(ps) == 2:
        a, b = ps
        fa = next((x for x in ps if x.forfeit), None)
        if fa is not None:
            m.winner_id = (b if fa is a else a).student_id
        elif a.score != b.score:
            m.winner_id = (a if a.score > b.score else b).student_id
        ra, rb = rating(db, a.student_id), rating(db, b.student_id)
        a.rating_before, b.rating_before = ra.rating, rb.rating
        sa = 0.5 if m.winner_id is None else 1.0 if m.winner_id == a.student_id else 0.0
        ea = _expected(ra.rating, rb.rating)
        ra.rating, rb.rating = ra.rating + K * (sa - ea), rb.rating + K * ((1 - sa) - (1 - ea))
        ra.games, rb.games = ra.games + 1, rb.games + 1
        a.rating_after, b.rating_after = ra.rating, rb.rating
    db.commit()


def _settle(db: Session, m: QuizMatch) -> None:
    """Resolve what time has changed: a stale queue entry is dropped, an expired match ends with what has been answered."""
    now = _now()
    if m.status == "waiting" and now - m.created_at > timedelta(seconds=WAIT_SECONDS):
        m.status, m.ended_at = "cancelled", now
        db.commit()
    elif m.status == "active" and m.deadline_at and now > m.deadline_at:
        _finish(db, m)


def _next_position(db: Session, m: QuizMatch, student_id: uuid.UUID) -> int:
    return len(db.scalars(select(QuizAnswer).where(QuizAnswer.match_id == m.id, QuizAnswer.student_id == student_id)).all())


def state(db: Session, p: Profile, match_id: uuid.UUID) -> dict:
    m, me = _match(db, p, match_id)
    _settle(db, m)
    ps = _players(db, m)
    opp = next((x for x in ps if x.student_id != p.id), None)
    out: dict = {"id": str(m.id), "status": m.status, "total": QUESTIONS, "myScore": me.score, "myAnswered": _next_position(db, m, p.id)}
    if opp is not None:
        op = db.get(Profile, opp.student_id)
        out["opponent"] = {"nickname": (op.nickname or "Classmate") if op else "Classmate", "avatar": op.avatar if op else None,
                           "answered": _next_position(db, m, opp.student_id), "score": opp.score, "finished": opp.finished}
    if m.status == "active":
        out["deadlineAt"] = m.deadline_at.isoformat()
        if not me.finished:
            item = db.get(Item, uuid.UUID(m.item_ids[out["myAnswered"]]))
            out["question"] = {"position": out["myAnswered"], **item_svc.public_item(item)}
    if m.status == "done":
        out["result"] = {"winnerId": str(m.winner_id) if m.winner_id else None, "youWon": m.winner_id == p.id, "draw": m.winner_id is None,
                         "ratingBefore": round(me.rating_before or 0), "ratingAfter": round(me.rating_after or 0), "forfeit": bool(opp and opp.forfeit),
                         "review": [_review(db, m, p.id, i) for i in range(QUESTIONS)] if m.item_ids else []}
    return out


def _review(db: Session, m: QuizMatch, student_id: uuid.UUID, pos: int) -> dict:
    item = db.get(Item, uuid.UUID(m.item_ids[pos]))
    a = db.get(QuizAnswer, (m.id, student_id, pos))
    return {"stem": item.stem, "correct": None if a is None else a.correct, "explanation": item.explanation}


def answer(db: Session, p: Profile, match_id: uuid.UUID, position: int, response: dict) -> dict:
    """Grade one answer. Answers go in order; sending the same position twice returns the first result, so a retry is safe."""
    m, me = _match(db, p, match_id)
    _settle(db, m)
    if m.status != "active":
        raise ClassError("This quiz is not running.", 409)
    done = db.get(QuizAnswer, (m.id, p.id, position))
    if done is not None:
        return {"correct": done.correct, "points": done.points, "finished": me.finished}
    if position != _next_position(db, m, p.id) or not 0 <= position < QUESTIONS:
        raise ClassError("That is not your next question.", 409)
    item = db.get(Item, uuid.UUID(m.item_ids[position]))
    ok = grading.grade(item.kind, item.answer_spec, response).correct
    last = db.scalar(select(QuizAnswer.created_at).where(QuizAnswer.match_id == m.id, QuizAnswer.student_id == p.id).order_by(QuizAnswer.position.desc()).limit(1))
    ms = int(max(0, (_now() - (last or m.started_at)).total_seconds() * 1000))
    points = (100 + int(50 * max(0.0, 1 - ms / 20000))) if ok else 0
    db.add(QuizAnswer(match_id=m.id, student_id=p.id, position=position, correct=ok, ms=ms, points=points))
    me.score += points
    me.finished = position == QUESTIONS - 1
    db.flush()
    if me.finished and all(x.finished for x in _players(db, m)):
        _finish(db, m)
    else:
        db.commit()
    return {"correct": ok, "points": points, "finished": me.finished}


def leave(db: Session, p: Profile, match_id: uuid.UUID) -> dict:
    """Leaving a queue cancels it. Leaving a running match forfeits it: the opponent wins."""
    m, me = _match(db, p, match_id)
    _settle(db, m)
    if m.status == "waiting":
        m.status, m.ended_at = "cancelled", _now()
        db.commit()
    elif m.status == "active":
        me.forfeit = True
        _finish(db, m)
    return state(db, p, m.id)


def standings(db: Session, p: Profile, class_id: uuid.UUID) -> dict:
    """The class's quiz table: nickname, avatar and quiz rating, for students who play. Opted-out students never appear."""
    c = access(db, p, class_id)
    rows = db.execute(select(QuizRating, Profile).join(Profile, Profile.id == QuizRating.student_id)
                      .join(QuizPlayer, QuizPlayer.student_id == Profile.id).join(QuizMatch, and_(QuizMatch.id == QuizPlayer.match_id, QuizMatch.classroom_id == c.id))
                      .where(Profile.league_opt_out.is_(False), QuizRating.games > 0).distinct().order_by(QuizRating.rating.desc()).limit(20)).all()
    return {"table": [{"nickname": pr.nickname or "Classmate", "avatar": pr.avatar, "rating": round(r.rating), "games": r.games, "you": pr.id == p.id} for r, pr in rows],
            "mine": round(rating(db, p.id).rating) if p.role == "student" else None}


def history(db: Session, p: Profile, limit: int = 20, before: datetime | None = None) -> list[dict]:
    """This student's finished battles, newest first. The opponent shows as nickname and avatar only."""
    q = (select(QuizMatch, Classroom).join(QuizPlayer, QuizPlayer.match_id == QuizMatch.id).join(Classroom, Classroom.id == QuizMatch.classroom_id)
         .where(QuizPlayer.student_id == p.id, QuizMatch.status == "done"))
    if before is not None:
        q = q.where(QuizMatch.ended_at < before)
    out = []
    for m, cls in db.execute(q.order_by(QuizMatch.ended_at.desc()).limit(max(1, min(limit, 50)))):
        ps = _players(db, m)
        me = next((x for x in ps if x.student_id == p.id), None)
        opp = next((x for x in ps if x.student_id != p.id), None)
        if me is None or opp is None:
            continue
        op = db.get(Profile, opp.student_id)
        out.append({"id": str(m.id), "classId": str(cls.id), "className": cls.name, "endedAt": m.ended_at.isoformat() if m.ended_at else None,
                    "opponent": {"nickname": (op.nickname or "Classmate") if op else "Classmate", "avatar": op.avatar if op else None},
                    "youWon": m.winner_id == p.id, "draw": m.winner_id is None, "forfeit": bool(opp.forfeit or me.forfeit),
                    "myScore": me.score, "theirScore": opp.score, "ratingBefore": round(me.rating_before or 0), "ratingAfter": round(me.rating_after or 0)})
    return out


def arena(db: Session, p: Profile) -> dict:
    """Everything the Arena page needs in one call: the student's classes with whether they can play, a running match if any, rating, record and recent battles."""
    if p.role != "student":
        raise ClassError("Only students play quizzes.", 403)
    rows = db.execute(select(Classroom).join(ClassMember, ClassMember.classroom_id == Classroom.id)
                      .where(ClassMember.student_id == p.id, ClassMember.status == "active").order_by(Classroom.name)).scalars().all()
    reason = None
    if p.consent_status not in ("granted", "not_required"):
        reason = "A parent, guardian or school needs to agree first."
    elif p.league_opt_out:
        reason = "You turned off competitive features in your settings."
    classes = []
    for c in rows:
        m = _mine(db, p, c)
        if m is not None:
            _settle(db, m)
        if m is not None and m.status not in ("waiting", "active"):
            m = None
        classes.append({"id": str(c.id), "name": c.name, "grade": c.grade, "subject": c.subject_id, "canPlay": reason is None and c.leagues_enabled,
                        "why": reason or (None if c.leagues_enabled else "Your teacher has turned off competitive features for this class."),
                        "matchId": str(m.id) if m else None, "matchStatus": m.status if m else None})
    games = history(db, p, 50)
    r = rating(db, p.id)
    db.commit()
    return {"rating": round(r.rating), "games": r.games, "wins": sum(g["youWon"] for g in games), "losses": sum(not g["youWon"] and not g["draw"] for g in games),
            "draws": sum(g["draw"] for g in games), "classes": classes, "recent": games[:5]}
