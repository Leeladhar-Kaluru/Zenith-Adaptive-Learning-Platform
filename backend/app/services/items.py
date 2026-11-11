"""Serialising items for students: never include the answer before they have answered."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine import grading
from app.models import Item, ItemConcept, Misconception, OptionMisconception


PATTERNS = {"mcq": "Multiple choice", "assertion": "Assertion and reason", "numeric": "Numerical", "case": "Case-based"}


def item_pattern(item) -> str:
    """How a question is asked, for Practice filters. Assertion-and-reason items are written with the standard 'Assertion (A): ... Reason (R): ...' stem."""
    if (getattr(item, "payload", None) or {}).get("pattern") == "case":
        return "case"
    if item.kind == "numeric":
        return "numeric"
    if item.kind == "mcq" and (item.stem or "").lstrip().startswith("Assertion (A)"):
        return "assertion"
    return "mcq" if item.kind == "mcq" else "other"


def public_item(item: Item) -> dict:
    return {"id": str(item.id), "kind": item.kind, "stem": item.stem, "difficulty": item.difficulty,
            "hintCount": len(item.hints or []), **grading.public_payload(item.kind, item.payload or {})}


def item_concepts(db: Session, item_id: uuid.UUID) -> list[tuple[str, float]]:
    return [(c, w) for c, w in db.execute(select(ItemConcept.concept_id, ItemConcept.weight).where(ItemConcept.item_id == item_id))]


def misconception_for(db: Session, item: Item, selected) -> Misconception | None:
    if item.kind != "mcq" or not selected:
        return None
    mid = db.scalar(select(OptionMisconception.misconception_id).where(OptionMisconception.item_id == item.id,
                                                                       OptionMisconception.option_key == str(selected).upper()))
    return db.get(Misconception, mid) if mid else None
