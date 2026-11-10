import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ConceptLevel, InteractionEvent, Item
from tests.conftest import make_profile


def _item(**kw):
    base = dict(key=f"gen:{uuid.uuid4()}", kind="mcq", stem="s", payload={}, answer_spec={"correct": "A"}, status="generated",
                origin="generated", content_hash=uuid.uuid4().hex, template_id="int_add", template_version=1, template_seed=1, level=1)
    base.update(kw)
    return Item(**base)


def test_duplicate_interaction_event_is_rejected(db):
    p = make_profile(db, "student")
    mk = lambda: InteractionEvent(student_id=p.id, client_event_id="e1", kind="hint_open", target_type="item", target_id="x", value={}, ms=0, occurred_at=datetime.now(timezone.utc))
    db.add(mk())
    db.commit()
    db.add(mk())
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_unknown_interaction_kind_is_rejected(db):
    p = make_profile(db, "student")
    db.add(InteractionEvent(student_id=p.id, client_event_id="e2", kind="mouse_wiggle", target_type="item", target_id="x", value={}, ms=0, occurred_at=datetime.now(timezone.utc)))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_generated_item_tuple_is_unique_and_level_bounded(db):
    db.add(_item())
    db.commit()
    db.add(_item())
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(_item(template_seed=2, level=6))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_concept_level_must_be_1_to_5(db):
    from app.models import Concept
    p = make_profile(db, "student")
    db.add(Concept(id="t-concept", title="T", grade=7, subject_id="maths"))
    db.commit()
    db.add(ConceptLevel(student_id=p.id, concept_id="t-concept", level=0))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
