"""Gap map for one student: the engine's ranking plus the lesson, practice and test links that act on each gap."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine import gaps as engine
from app.models import Chapter, ChapterConcept, Concept, Profile
from app.services import library
from app.services import states as st_svc


def gap_map(db: Session, profile: Profile) -> dict:
    stt = st_svc.states(db, profile.id)
    in_class = {c for (c,) in db.execute(select(ChapterConcept.concept_id).join(Chapter, Chapter.id == ChapterConcept.chapter_id)
                                        .where(Chapter.status == "published", Chapter.grade == profile.grade))}
    ids = in_class | set(stt)
    concepts = {c.id: {"title": c.title, "grade": c.grade} for c in db.scalars(select(Concept).where(Concept.id.in_(ids)))} if ids else {}
    result = engine.rank_gaps(concepts, st_svc.edges(db), stt)

    def lesson_href(cid: str) -> str | None:
        les = library._lesson_for_concept(db, cid)
        return f"/lesson/{les['lessonId']}" if les else None

    for g in result["gaps"]:
        target = g["root"]["id"] if g["root"] else g["conceptId"]
        g["actions"] = {"lesson": lesson_href(target), "practice": f"/practice?concept={g['conceptId']}", "test": f"/tests/new?kind=topic_test&concept={g['conceptId']}",
                        "startWith": g["root"]["title"] if g["root"] else None}
    result["evidence"] = sum(s["n"] for c, s in stt.items() if c in concepts)
    return result
