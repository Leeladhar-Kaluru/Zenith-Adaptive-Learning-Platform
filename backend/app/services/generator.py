"""Serve generated questions: pick a concept and level from the student's evidence, build the question, store it so it can be replayed."""
from __future__ import annotations

import hashlib
import json
import random
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine import bkt
from app.engine.templates import InvalidInstance, Instance, generate, templates_for
from app.models import ConceptLevel, EvidenceEvent, Item, ItemConcept, Misconception, OptionMisconception, Profile

GENERATED = "generated"
BETA = {1: -1.5, 2: -0.75, 3: 0.0, 4: 0.75, 5: 1.5}
DIFFICULTY = {1: "intro", 2: "intro", 3: "standard", 4: "standard", 5: "challenge"}


def _hash(inst: Instance) -> str:
    blob = json.dumps([inst.stem, inst.payload, inst.answer_spec], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def materialise(db: Session, inst: Instance) -> Item:
    """Store the instance as an ordinary item (idempotent): grading, evidence and BKT then work unchanged."""
    row = db.scalar(select(Item).where(Item.origin == GENERATED, Item.template_id == inst.template_id, Item.template_version == inst.version,
                                       Item.template_seed == inst.seed, Item.level == inst.level))
    if row:
        return row
    row = Item(key=f"gen:{inst.template_id}:{inst.version}:{inst.seed}:{inst.level}", version=1, kind=inst.kind, stem=inst.stem,
               payload=inst.payload, answer_spec=inst.answer_spec, explanation=inst.explanation, hints=inst.hints,
               difficulty=DIFFICULTY[inst.level], beta=BETA[inst.level], purpose="practice", status="generated", origin=GENERATED,
               content_hash=_hash(inst), template_id=inst.template_id, template_version=inst.version, template_seed=inst.seed, level=inst.level)
    db.add(row)
    db.flush()
    db.add(ItemConcept(item_id=row.id, concept_id=inst.concept, weight=1.0))
    for key, (code, desc) in inst.misconceptions.items():
        m = db.scalar(select(Misconception).where(Misconception.concept_id == inst.concept, Misconception.code == code))
        if m is None:
            m = Misconception(concept_id=inst.concept, code=code, description=desc)
            db.add(m)
            db.flush()
        db.add(OptionMisconception(item_id=row.id, option_key=key, misconception_id=m.id))
    db.flush()
    return row


def start_level(p_known: float | None) -> int:
    """Where to start a concept the student has no ladder row for yet, inferred from the learner model."""
    if p_known is None:
        return 1
    return 1 if p_known < 0.4 else 2 if p_known < 0.6 else 3 if p_known < 0.8 else 4


def level_for(db: Session, student_id: uuid.UUID, concept_id: str, p_known: float | None) -> tuple[int, str]:
    row = db.get(ConceptLevel, (student_id, concept_id))
    if row:
        return row.level, row.reason
    return start_level(p_known), ""


def next_generated(db: Session, profile: Profile, concept_ids: list[str], states: dict[str, dict], *, harder: bool = False,
                   recent: set[str] | None = None, rng: random.Random | None = None) -> tuple[Item, int, str] | None:
    """Return (item, level, reason) or None, in which case the caller serves a stored question instead."""
    rng = rng or random.Random()
    recent = recent or set()
    options = [c for c in concept_ids if templates_for(c)]
    if not options:
        return None
    # work where the learner model says help is most needed; unseen concepts come first
    concept = min(options, key=lambda c: (states.get(c, {}).get("p", bkt.P_INIT), rng.random()))
    level, reason = level_for(db, profile.id, concept, states.get(concept, {}).get("p"))
    if harder:
        level = min(5, level + 1)
    for _ in range(8):
        tpl = rng.choice(templates_for(concept))
        seed = rng.randrange(1 << 30)
        try:
            inst = generate(tpl.id, seed, level)
        except (InvalidInstance, ValueError):
            continue
        item = materialise(db, inst)
        if str(item.id) in recent:
            continue
        return item, level, reason
    return None


def seen_item_ids(db: Session, student_id: uuid.UUID) -> set[str]:
    return {str(i) for (i,) in db.execute(select(EvidenceEvent.item_id).where(EvidenceEvent.student_id == student_id))}
