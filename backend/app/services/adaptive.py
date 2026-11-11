"""Adaptive check service. Stateless: the app sends when the check started, and the answers already recorded since then are the state.

Each call re-estimates ability from those real answers, decides whether to stop, and otherwise picks the most informative unanswered question."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine import adaptive as eng
from app.models import Concept, EvidenceEvent, Item, Profile, Subject
from app.services import items as item_svc
from app.services import practice
from app.services import states as st_svc


def step(db: Session, p: Profile, *, chapter: str | None, concept: str | None, subject: str | None, since: datetime) -> dict:
    ids, scope = practice.scope_concepts(db, p, chapter, concept, False, False)
    if subject:
        if not db.get(Subject, subject):
            raise practice.PracticeError("Unknown subject.", 422)
        ids = [c for c in ids if (db.get(Concept, c) or Concept()).subject_id == subject]
    if not ids:
        raise practice.PracticeError("No questions are ready for this yet.", 409)
    cands = practice.pool(db, ids, ("check", "practice", "probe", "test"))
    by_id = {c["id"]: c for c in cands}
    rows = db.execute(select(EvidenceEvent.item_id, EvidenceEvent.correct).where(EvidenceEvent.student_id == p.id, EvidenceEvent.occurred_at >= since)
                      .order_by(EvidenceEvent.occurred_at)).all()
    answered = [(str(i), ok) for i, ok in rows if str(i) in by_id]
    first = {}
    for i, ok in answered:                      # only the first answer to a question counts, so re-asking cannot change the estimate
        first.setdefault(i, ok)
    resp = [(by_id[i]["beta"], ok) for i, ok in first.items()]
    subject_id = db.get(Concept, ids[0]).subject_id
    prior = st_svc.theta(db, p.id, subject_id)
    theta, se = eng.estimate(resp, prior_mean=prior)
    left = [c for c in cands if c["id"] not in first]
    stop, why = eng.should_stop(len(first), se, len(left))
    lo, hi = eng.interval(theta, se)
    out = {"model": eng.MODEL_VERSION, "scope": scope, "answered": len(first), "right": sum(first.values()), "ability": round(theta, 2), "se": round(se, 2),
           "interval": [round(lo, 2), round(hi, 2)], "level": eng.describe(theta), "done": stop, "reason": why}
    if stop:
        per: dict[str, list[int]] = {}
        for i, ok in first.items():
            primary = max(by_id[i]["concepts"], key=lambda cw: cw[1])[0]
            per.setdefault(primary, [0, 0])
            per[primary][0] += int(ok)
            per[primary][1] += 1
        titles = {c.id: c.title for c in db.scalars(select(Concept).where(Concept.id.in_(list(per) or ["-"])))}
        out["topics"] = [{"id": c, "title": titles.get(c, c), "right": r, "total": n, "practice": f"/practice?concept={c}"} for c, (r, n) in per.items()]
        return out
    seen: dict[str, int] = {}
    for i in first:
        primary = max(by_id[i]["concepts"], key=lambda cw: cw[1])[0]
        seen[primary] = seen.get(primary, 0) + 1
    nxt = eng.choose(left, theta, seen)
    item = db.get(Item, nxt["id"])
    out["item"] = item_svc.public_item(item)
    out["why"] = "Chosen to be close to your level, so each answer tells us as much as possible." if first else "A first question near your current level."
    return out
