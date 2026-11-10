import uuid

import pytest
from sqlalchemy import func, select

from app.engine import grading
from app.engine.templates import generate
from app.models import ConceptLevel, EvidenceEvent, Item, Concept
from app.services import generator
from tests.conftest import auth, make_profile

API = "/api/v1"
CONCEPT = "integers-add"


@pytest.fixture()
def student(db, client):
    p = make_profile(db, "student", grade=6)
    if not db.get(Concept, CONCEPT):
        db.add(Concept(id=CONCEPT, title="Adding integers", grade=6, subject_id="maths"))
        db.commit()
    return p


def serve(client, p, **q):
    r = client.get(f"{API}/practice/next", params={"concept": CONCEPT, **q}, headers=auth(p))
    assert r.status_code == 200, r.text
    return r.json()


def answer(client, p, db, served, *, right: bool, hints=0, ms=9000):
    item = db.get(Item, uuid.UUID(served["item"]["id"]))
    correct = item.answer_spec["correct"]
    choice = correct if right else next(o["key"] for o in item.payload["options"] if o["key"] != correct)
    r = client.post(f"{API}/evidence", headers=auth(p), json={"itemId": str(item.id), "response": {"choice": choice}, "hintsUsed": hints, "ms": ms,
                                                                "context": "solve", "clientEventId": uuid.uuid4().hex})
    assert r.status_code == 200, r.text
    return r.json()


def test_new_student_gets_a_level_one_generated_question(db, client, student):
    s = serve(client, student)
    assert s["generated"] is True and s["ladderLevel"] == 1
    assert "correct" not in s["item"] and "answer_spec" not in s["item"]
    assert s["item"]["kind"] == "mcq" and len(s["item"]["options"]) >= 3


def test_two_clean_correct_answers_raise_the_level_and_questions_get_harder(db, client, student):
    for _ in range(2):
        out = answer(client, student, db, serve(client, student), right=True)
    assert out["levelChange"] and out["levelChange"]["to"] == 2 and out["levelChange"]["reason"]
    assert serve(client, student)["ladderLevel"] == 2


def test_two_wrong_answers_lower_the_level(db, client, student):
    db.add(ConceptLevel(student_id=student.id, concept_id=CONCEPT, level=3, streak_up=0, streak_down=0, reason=""))
    db.commit()
    answer(client, student, db, serve(client, student), right=False)
    out = answer(client, student, db, serve(client, student), right=False)
    assert out["levelChange"]["to"] == 2
    assert out["misconception"] is not None or out["feedback"]


def test_hinted_correct_does_not_level_up(db, client, student):
    for _ in range(3):
        out = answer(client, student, db, serve(client, student), right=True, hints=1)
    assert out["levelChange"] is None
    assert db.get(ConceptLevel, (student.id, CONCEPT)).level == 1


def test_students_get_different_questions_and_same_instance_is_stored_once(db, client, student):
    other = make_profile(db, "student", grade=6)
    stems = {serve(client, student)["item"]["stem"] for _ in range(6)} | {serve(client, other)["item"]["stem"] for _ in range(6)}
    assert len(stems) > 3
    inst = generate("int_add", 5, 1)
    a, b = generator.materialise(db, inst), generator.materialise(db, inst)
    db.commit()
    assert a.id == b.id
    assert db.scalar(select(func.count(Item.id)).where(Item.template_id == "int_add", Item.template_seed == 5, Item.level == 1)) == 1


def test_evidence_on_generated_item_grades_server_side_and_is_idempotent(db, client, student):
    s = serve(client, student)
    item = db.get(Item, uuid.UUID(s["item"]["id"]))
    cid = uuid.uuid4().hex
    body = {"itemId": str(item.id), "response": {"choice": item.answer_spec["correct"]}, "hintsUsed": 0, "ms": 5000, "context": "solve", "clientEventId": cid}
    r1 = client.post(f"{API}/evidence", headers=auth(student), json=body).json()
    r2 = client.post(f"{API}/evidence", headers=auth(student), json=body).json()
    assert r1["correct"] is True and r2["alreadyRecorded"] is True
    assert db.scalar(select(func.count(EvidenceEvent.id)).where(EvidenceEvent.client_event_id == cid)) == 1


def test_hint_endpoint_serves_generated_items(db, client, student):
    s = serve(client, student)
    r = client.get(f"{API}/items/{s['item']['id']}/hint", params={"n": 1}, headers=auth(student))
    assert r.status_code == 200 and r.json()["hint"]


def test_falls_back_when_generation_cannot_produce_a_question(db, client, student, monkeypatch):
    monkeypatch.setattr(generator, "generate", lambda *a, **k: (_ for _ in ()).throw(generator.InvalidInstance("broken")))
    r = client.get(f"{API}/practice/next", params={"concept": CONCEPT}, headers=auth(student))
    assert r.status_code == 409                       # no stored question either: an honest message, never a broken question


def test_harder_flag_raises_level_by_one(db, client, student):
    assert serve(client, student, harder="true")["ladderLevel"] == 2
