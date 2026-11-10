import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models import InteractionEvent
from app.services import interactions
from tests.conftest import auth, make_profile

API = "/api/v1"


def ev(kind="hint_open", cid=None, **kw):
    return {"clientEventId": cid or uuid.uuid4().hex, "kind": kind, "targetType": "item", "targetId": "abc", "value": {}, "ms": 10, **kw}


def count(db, p):
    return db.scalar(select(func.count(InteractionEvent.id)).where(InteractionEvent.student_id == p.id))


def test_stores_events_and_ignores_duplicates(db, client):
    p = make_profile(db, "student")
    e = ev(cid="same-id-1")
    r = client.post(f"{API}/interactions/batch", headers=auth(p), json={"events": [e, ev("dwell"), e]}).json()
    assert r["stored"] == 2 and r["ignored"] == 1
    assert client.post(f"{API}/interactions/batch", headers=auth(p), json={"events": [e]}).json()["stored"] == 0
    assert count(db, p) == 2


def test_more_than_200_events_is_rejected(db, client):
    p = make_profile(db, "student")
    r = client.post(f"{API}/interactions/batch", headers=auth(p), json={"events": [ev() for _ in range(201)]})
    assert r.status_code == 422


def test_daily_cap(db, client, monkeypatch):
    p = make_profile(db, "student")
    monkeypatch.setattr(interactions, "MAX_PER_DAY", 5)
    r = client.post(f"{API}/interactions/batch", headers=auth(p), json={"events": [ev() for _ in range(8)]}).json()
    assert r["stored"] == 5 and r["dailyLimitReached"] is True
    assert client.post(f"{API}/interactions/batch", headers=auth(p), json={"events": [ev()]}).json()["stored"] == 0


def test_without_consent_is_forbidden(db, client):
    p = make_profile(db, "student")
    p.consent_status = "pending"
    db.commit()
    assert client.post(f"{API}/interactions/batch", headers=auth(p), json={"events": [ev()]}).status_code == 403


def test_teacher_cannot_post_and_unknown_kind_is_dropped(db, client):
    t = make_profile(db, "teacher")
    assert client.post(f"{API}/interactions/batch", headers=auth(t), json={"events": [ev()]}).status_code == 403
    p = make_profile(db, "student")
    r = client.post(f"{API}/interactions/batch", headers=auth(p), json={"events": [ev("mouse_wiggle")]}).json()
    assert r["stored"] == 0


def test_future_timestamps_and_huge_values_are_clamped(db, client):
    p = make_profile(db, "student")
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    client.post(f"{API}/interactions/batch", headers=auth(p), json={"events": [ev(occurredAt=future, value={"x": "y" * 5000})]})
    row = db.scalar(select(InteractionEvent).where(InteractionEvent.student_id == p.id))
    assert row.occurred_at <= datetime.now(timezone.utc) and row.value == {}


def test_struggle_signals_change_the_ladder(db, client):
    """Interaction events recorded for an item feed the ladder: two hint opens make a single wrong answer lower the level."""
    from app.models import Concept, ConceptLevel, Item
    from app.services import generator
    from app.engine.templates import generate
    p = make_profile(db, "student", grade=6)
    db.add(Concept(id="integers-add", title="Adding integers", grade=6, subject_id="maths"))
    db.commit()
    item = generator.materialise(db, generate("int_add", 11, 3))
    db.add(ConceptLevel(student_id=p.id, concept_id="integers-add", level=3, streak_up=0, streak_down=0, reason=""))
    db.commit()
    t = datetime.now(timezone.utc).isoformat()
    client.post(f"{API}/interactions/batch", headers=auth(p), json={"events": [
        {**ev("hint_open"), "targetId": str(item.id), "occurredAt": t}, {**ev("hint_open"), "targetId": str(item.id), "occurredAt": t}]})
    wrong = next(o["key"] for o in item.payload["options"] if o["key"] != item.answer_spec["correct"])
    r = client.post(f"{API}/evidence", headers=auth(p), json={"itemId": str(item.id), "response": {"choice": wrong}, "hintsUsed": 2, "ms": 20000,
                                                              "context": "solve", "clientEventId": uuid.uuid4().hex}).json()
    assert r["levelChange"]["to"] == 2 and "hint" in r["levelChange"]["reason"].lower()


def test_teacher_sees_levels_and_activity_for_own_student_only(db, client):
    from app.models import ClassMember, Classroom, Concept, ConceptLevel
    t = make_profile(db, "teacher")
    other = make_profile(db, "teacher")
    st = make_profile(db, "student", grade=6)
    c = Classroom(teacher_id=t.id, name="6A", grade=6, subject_id="maths", board_id="cbse", join_code="ZEN-TEST")
    db.add(c)
    db.add(Concept(id="integers-add", title="Adding integers", grade=6, subject_id="maths"))
    db.commit()
    db.add(ClassMember(classroom_id=c.id, student_id=st.id))
    db.add(ConceptLevel(student_id=st.id, concept_id="integers-add", level=3, streak_up=0, streak_down=0, reason="2 correct answers in a row without hints, so questions get harder."))
    db.commit()
    client.post(f"{API}/interactions/batch", headers=auth(st), json={"events": [ev("hint_open"), ev("sim_change"), ev("dwell", ms=120000)]})
    r = client.get(f"{API}/teacher/classes/{c.id}/students/{st.id}", headers=auth(t))
    assert r.status_code == 200
    body = r.json()
    assert body["levels"][0]["level"] == 3 and "harder" in body["levels"][0]["reason"]
    assert body["activity"]["hintsOpened"] == 1 and body["activity"]["simulationMoves"] == 1 and body["activity"]["readingMinutes"] == 2.0
    assert client.get(f"{API}/teacher/classes/{c.id}/students/{st.id}", headers=auth(other)).status_code in (403, 404)
