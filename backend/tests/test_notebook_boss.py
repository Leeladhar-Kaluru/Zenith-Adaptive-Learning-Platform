import uuid

import pytest
from sqlalchemy import select

from app.models import Chapter, ChapterConcept, Concept, ConceptState, CurriculumVersion, Item
from tests.conftest import auth, make_profile

API = "/api/v1"
C1, C2 = "integers-add", "simple-equation-one-step"


@pytest.fixture()
def world(db, client):
    p = make_profile(db, "student", grade=7)
    for cid, title in ((C1, "Adding integers"), (C2, "One-step equations")):
        if not db.get(Concept, cid):
            db.add(Concept(id=cid, title=title, grade=7, subject_id="maths"))
    db.flush()
    cv = db.scalar(select(CurriculumVersion))
    if cv is None:
        cv = CurriculumVersion(board_id="cbse", label="t", effective_year=2025, verified=True)
        db.add(cv)
        db.flush()
    ch = Chapter(slug="boss-test", version_id=cv.id, grade=7, subject_id="maths", title="Boss test", summary="s", status="published")
    db.add(ch)
    db.flush()
    db.add_all([ChapterConcept(chapter_id=ch.id, concept_id=C1, role="core"), ChapterConcept(chapter_id=ch.id, concept_id=C2, role="core")])
    db.commit()
    return p


def set_state(db, p, cid, pk, n):
    db.merge(ConceptState(student_id=p.id, concept_id=cid, p_known=pk, n_obs=n, n_correct=n, streak=n, status="secure" if pk > 0.8 else "learning", param_version="t"))
    db.commit()


def serve(client, p, concept):
    return client.get(f"{API}/practice/next", params={"concept": concept}, headers=auth(p)).json()


def answer(client, db, p, served, right):
    item = db.get(Item, uuid.UUID(served["item"]["id"]))
    ok = item.answer_spec["correct"]
    choice = ok if right else next(o["key"] for o in item.payload["options"] if o["key"] != ok)
    return client.post(f"{API}/evidence", headers=auth(p), json={"itemId": str(item.id), "response": {"choice": choice}, "hintsUsed": 0, "ms": 8000,
                                                                "context": "solve", "clientEventId": uuid.uuid4().hex}).json()


def test_boss_is_locked_without_evidence_then_below_threshold_then_open(db, client, world):
    r = client.get(f"{API}/boss/boss-test", headers=auth(world)).json()
    assert r["unlocked"] is False and "at least 3 questions" in r["reason"]
    set_state(db, world, C1, 0.5, 5)
    set_state(db, world, C2, 0.6, 5)
    r = client.get(f"{API}/boss/boss-test", headers=auth(world)).json()
    assert r["unlocked"] is False and "55%" in r["reason"] and r["needed"] == 0.7
    locked = client.post(f"{API}/assessments", headers=auth(world), json={"kind": "boss", "chapter": "boss-test"})
    assert locked.status_code == 409
    set_state(db, world, C1, 0.9, 6)
    set_state(db, world, C2, 0.8, 6)
    assert client.get(f"{API}/boss/boss-test", headers=auth(world)).json()["unlocked"] is True


def test_boss_session_uses_hard_generated_questions_and_reports_pass(db, client, world):
    set_state(db, world, C1, 0.9, 6)
    set_state(db, world, C2, 0.85, 6)
    s = client.post(f"{API}/assessments", headers=auth(world), json={"kind": "boss", "chapter": "boss-test"})
    assert s.status_code == 200, s.text
    sess = s.json()
    assert sess["kind"] == "boss" and sess["total"] >= 6
    items = [db.get(Item, uuid.UUID(i["id"])) for i in sess["items"]]
    assert all(it.origin == "generated" and it.level >= 4 for it in items)
    for it in items:
        client.post(f"{API}/evidence", headers=auth(world), json={"itemId": str(it.id), "response": {"choice": it.answer_spec["correct"]}, "hintsUsed": 0, "ms": 9000,
                                                                  "context": "test", "clientEventId": uuid.uuid4().hex, "sessionId": sess["id"]})
    done = client.post(f"{API}/assessments/{sess['id']}/submit", headers=auth(world)).json()
    assert done["summary"]["boss"] is True and done["summary"]["passed"] is True and done["summary"]["accuracy"] == 1.0


def test_boss_fail_is_reported_honestly(db, client, world):
    set_state(db, world, C1, 0.9, 6)
    set_state(db, world, C2, 0.85, 6)
    sess = client.post(f"{API}/assessments", headers=auth(world), json={"kind": "boss", "chapter": "boss-test"}).json()
    for it in sess["items"]:
        item = db.get(Item, uuid.UUID(it["id"]))
        wrong = next(o["key"] for o in item.payload["options"] if o["key"] != item.answer_spec["correct"])
        client.post(f"{API}/evidence", headers=auth(world), json={"itemId": str(item.id), "response": {"choice": wrong}, "hintsUsed": 0, "ms": 9000,
                                                                  "context": "test", "clientEventId": uuid.uuid4().hex, "sessionId": sess["id"]})
    done = client.post(f"{API}/assessments/{sess['id']}/submit", headers=auth(world)).json()
    assert done["summary"]["passed"] is False and done["summary"]["mistakes"]


def test_unpublished_or_unknown_chapter_is_404(db, client, world):
    assert client.get(f"{API}/boss/nope", headers=auth(world)).status_code == 404


def test_notebook_groups_by_misconception_and_closes_after_three_right(db, client, world):
    for _ in range(3):
        answer(client, db, world, serve(client, world, C1), right=False)
    nb = client.get(f"{API}/progress/notebook", headers=auth(world)).json()
    assert nb["openCount"] >= 1
    g = nb["groups"][0]
    assert g["misconception"] and g["times"] >= 1 and g["examples"] and g["practice"].startswith("/practice?concept=")
    assert all(not x["resolved"] for x in nb["groups"])
    set_state(db, world, C1, 0.9, 4)                              # streak of 4 correct
    after = client.get(f"{API}/progress/notebook", headers=auth(world)).json()
    assert after["openCount"] == 0 and after["resolvedCount"] >= 1
    assert client.get(f"{API}/progress/notebook", params={"resolved": "true"}, headers=auth(world)).json()["groups"]


def test_notebook_is_private_to_the_student(db, client, world):
    answer(client, db, world, serve(client, world, C1), right=False)
    other = make_profile(db, "student", grade=7)
    assert client.get(f"{API}/progress/notebook", headers=auth(other)).json()["groups"] == []
