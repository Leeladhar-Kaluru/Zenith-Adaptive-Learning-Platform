"""Read helpers for the learner model."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine import bkt, graph
from app.models import Concept, ConceptEdge, ConceptState, LearnerRating


def edges(db: Session) -> list[tuple[str, str]]:
    return [(a, b) for a, b in db.execute(select(ConceptEdge.prereq_id, ConceptEdge.concept_id))]


def states(db: Session, student_id: uuid.UUID, concept_ids: list[str] | None = None) -> dict[str, dict]:
    q = select(ConceptState).where(ConceptState.student_id == student_id)
    if concept_ids is not None:
        q = q.where(ConceptState.concept_id.in_(concept_ids))
    return {s.concept_id: {"p": s.p_known, "n": s.n_obs, "c": s.n_correct, "status": s.status, "streak": s.streak, "last": s.last_obs_at}
            for s in db.scalars(q)}


def band(st: dict | None) -> str:
    return st["status"] if st else "unassessed"


def theta(db: Session, student_id: uuid.UUID, subject_id: str) -> float:
    r = db.get(LearnerRating, (student_id, subject_id))
    return r.theta if r else 0.0


def root_gap(db: Session, student_id: uuid.UUID, concept_ids: list[str]) -> dict | None:
    """The deepest weak prerequisite beneath any of these concepts, with evidence, or None."""
    e = edges(db)
    st = states(db, student_id)
    for cid in concept_ids:
        own = st.get(cid)
        if own and own["status"] in ("gap_suspected", "gap_confirmed", "learning") and own["n"] >= 2 and own["p"] < 0.55 or not own:
            res = graph.investigate(cid, e, st)
            if res["root"]:
                c = db.get(Concept, res["root"])
                s = st[res["root"]]
                return {"concept": c, "state": s, "target": cid}
    return None
