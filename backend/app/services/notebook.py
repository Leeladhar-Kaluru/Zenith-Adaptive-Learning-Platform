"""Mistake notebook grouped by the underlying misunderstanding, not by individual question."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Concept, ConceptState, EvidenceEvent, Item, Misconception

RESOLVED_STREAK = 3          # this many correct answers in a row on the topic closes a mistake group


def notebook(db: Session, student_id: uuid.UUID, include_resolved: bool = False) -> dict:
    """Wrong answers grouped by misconception, newest first, each with a concrete example, the explanation and a way to practise it."""
    rows = db.execute(select(EvidenceEvent, Misconception).join(Misconception, Misconception.id == EvidenceEvent.misconception_id)
                      .where(EvidenceEvent.student_id == student_id, EvidenceEvent.correct.is_(False))
                      .order_by(EvidenceEvent.occurred_at.desc())).all()
    groups: dict[uuid.UUID, dict] = {}
    for ev, m in rows:
        g = groups.setdefault(m.id, {"misconception": m.description, "code": m.code, "conceptId": m.concept_id, "times": 0, "lastAt": ev.occurred_at, "examples": []})
        g["times"] += 1
        if len(g["examples"]) < 2 and ev.item_id not in {e["_id"] for e in g["examples"]}:
            item = db.get(Item, ev.item_id)
            g["examples"].append({"_id": ev.item_id, "stem": item.stem, "explanation": item.explanation})
    states = {s.concept_id: s for s in db.scalars(select(ConceptState).where(ConceptState.student_id == student_id))}
    out, resolved = [], 0
    for g in groups.values():
        st = states.get(g["conceptId"])
        done = bool(st and st.streak >= RESOLVED_STREAK)
        resolved += 1 if done else 0
        if done and not include_resolved:
            continue
        con = db.get(Concept, g["conceptId"])
        out.append({"misconception": g["misconception"], "code": g["code"], "concept": {"id": g["conceptId"], "title": con.title if con else g["conceptId"]},
                    "times": g["times"], "lastAt": g["lastAt"].isoformat(), "resolved": done,
                    "examples": [{k: v for k, v in e.items() if k != "_id"} for e in g["examples"]],
                    "practice": f"/practice?concept={g['conceptId']}"})
    out.sort(key=lambda x: (x["resolved"], x["lastAt"]), reverse=False)
    out.sort(key=lambda x: x["lastAt"], reverse=True)
    out.sort(key=lambda x: x["resolved"])
    return {"groups": out, "openCount": sum(1 for x in out if not x["resolved"]), "resolvedCount": resolved,
            "note": "Groups close when you get the topic right three times in a row."}
