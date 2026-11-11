"""The student's profile dashboard: one read that turns the evidence log and concept states into plain numbers.
Every figure is computed from the student's own rows (evidence_events, concept_states, daily_activity, quiz tables). Nothing is estimated for display."""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine import bkt, streaks
from app.models import Concept, EvidenceEvent, Item, Profile, Subject
from app.services import engage, home, quiz
from app.services import states as st_svc

WINDOW_DAYS = 14
FAST_WRONG_MS = 2000          # a wrong answer this quick is treated as a guess, and is shown as such


def _median(xs: list[int]) -> int | None:
    return int(statistics.median(xs)) if xs else None


def build(db: Session, p: Profile) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=max(WINDOW_DAYS, 30))
    ev = db.execute(select(EvidenceEvent.occurred_at, EvidenceEvent.correct, EvidenceEvent.ms, EvidenceEvent.hints_used, Item.difficulty)
                    .join(Item, Item.id == EvidenceEvent.item_id).where(EvidenceEvent.student_id == p.id, EvidenceEvent.occurred_at >= since)).all()

    by_day: dict[str, dict] = defaultdict(lambda: {"answers": 0, "correct": 0, "ms": 0})
    for at, ok, ms, _h, _d in ev:
        d = by_day[at.astimezone(timezone.utc).date().isoformat()]
        d["answers"] += 1
        d["correct"] += int(ok)
        d["ms"] += min(ms or 0, 120000)           # one forgotten tab must not count as an hour of study
    days = []
    for i in range(WINDOW_DAYS - 1, -1, -1):
        key = (now - timedelta(days=i)).date().isoformat()
        d = by_day.get(key, {"answers": 0, "correct": 0, "ms": 0})
        days.append({"day": key, "answers": d["answers"], "correct": d["correct"], "minutes": round(d["ms"] / 60000, 1)})
    today = days[-1]

    right = [ms for _, ok, ms, _, _ in ev if ok and ms]
    wrong = [ms for _, ok, ms, _, _ in ev if not ok and ms]
    by_diff: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for _, ok, _, _, diff in ev:
        by_diff[diff][0] += int(ok)
        by_diff[diff][1] += 1
    pace = {"answers30d": len(ev), "medianMsRight": _median(right), "medianMsWrong": _median(wrong),
            "hintRate": round(sum(1 for e in ev if e[3] > 0) / len(ev), 3) if ev else None,
            "guessRate": round(sum(1 for _, ok, ms, _, _ in ev if not ok and ms and ms < FAST_WRONG_MS) / len(ev), 3) if ev else None,
            "byDifficulty": [{"level": k, "right": by_diff[k][0], "total": by_diff[k][1]} for k in ("intro", "standard", "challenge") if by_diff[k][1]]}

    stt = st_svc.states(db, p.id)
    concepts = {c.id: c for c in db.scalars(select(Concept).where(Concept.id.in_(list(stt)) if stt else Concept.id == "-"))}
    names = dict(db.execute(select(Subject.id, Subject.name)).all())
    subj: dict[str, dict] = {}
    for cid, s in stt.items():
        c = concepts.get(cid)
        if c is None:
            continue
        row = subj.setdefault(c.subject_id, {"id": c.subject_id, "name": names.get(c.subject_id, c.subject_id), "topics": 0, "bands": defaultdict(int), "p": 0.0, "answers": 0, "correct": 0})
        row["topics"] += 1
        row["bands"][s["status"]] += 1
        row["p"] += s["p"]
        row["answers"] += s["n"]
        row["correct"] += s["c"]
    subjects = [{"id": r["id"], "name": r["name"], "topics": r["topics"], "bands": dict(r["bands"]), "understanding": round(r["p"] / r["topics"], 3),
                 "answers": r["answers"], "accuracy": round(r["correct"] / r["answers"], 3) if r["answers"] else None,
                 "rating": round(st_svc.theta(db, p.id, r["id"]), 2)} for r in sorted(subj.values(), key=lambda r: r["name"])]

    def topic(cid: str) -> dict:
        s, c = stt[cid], concepts[cid]
        return {"id": cid, "title": c.title, "subject": c.subject_id, "grade": c.grade, "understanding": round(s["p"], 3), "answers": s["n"], "correct": s["c"],
                "band": s["status"], "confidence": bkt.uncertainty(s["n"]), "practice": f"/practice?concept={cid}"}
    seen = [cid for cid in stt if cid in concepts and stt[cid]["n"] >= 3]
    focus = [topic(c) for c in sorted((c for c in seen if stt[c]["p"] < 0.8), key=lambda c: stt[c]["p"])[:5]]
    strong = [topic(c) for c in sorted((c for c in seen if stt[c]["p"] >= 0.8), key=lambda c: -stt[c]["p"])[:3]]

    games = quiz.history(db, p, 50)
    r = quiz.rating(db, p.id)
    db.commit()
    return {
        "generatedAt": now.isoformat(),
        "me": {"nickname": p.nickname, "avatar": p.avatar, "grade": p.grade, "xp": streaks.level(engage.total_xp(db, p.id)), "streak": engage.streak_info(db, p.id)},
        "today": today, "days": days, "pace": pace, "subjects": subjects, "focus": focus, "strong": strong,
        "revisionDue": len(home.due_revision(db, p.id)), "openMistakes": home.mistake_count(db, p.id),
        "battles": {"rating": round(r.rating), "games": r.games, "wins": sum(g["youWon"] for g in games), "draws": sum(g["draw"] for g in games),
                    "losses": sum(not g["youWon"] and not g["draw"] for g in games), "recent": games[:5]},
    }
