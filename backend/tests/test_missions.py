from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Chapter, ChapterConcept, Concept, ConceptState, RevisionSchedule
from tests.conftest import auth, make_profile
from tests.test_api import publish_all

API = "/api/v1"


@pytest.fixture()
def student(db, client, tmp_path):
    publish_all(db, tmp_path, make_profile(db, "reviewer"))
    return make_profile(db, "student", grade=7)


def chapter_concepts(db):
    """Every topic of every published chapter (the stretch step needs all of them secure)."""
    return sorted({c for (c,) in db.execute(select(ChapterConcept.concept_id).join(Chapter, Chapter.id == ChapterConcept.chapter_id).where(Chapter.status == "published"))})


def mission(client, p):
    r = client.get(f"{API}/mission", headers=auth(p))
    assert r.status_code == 200, r.text
    return r.json()


def test_a_brand_new_student_is_sent_to_the_quick_check_first(db, client, student):
    m = mission(client, student)
    assert m["items"] == [] and "quick check" in m["reason"].lower() and m["href"].startswith("/tests/new?kind=diagnostic")


def test_mission_has_revision_then_new_then_challenge_each_with_a_reason(db, client, student):
    cids = chapter_concepts(db)
    for c in cids:
        db.add(ConceptState(student_id=student.id, concept_id=c, p_known=0.93, n_obs=6, n_correct=6, streak=6, status="secure", param_version="t",
                            last_obs_at=datetime.now(timezone.utc)))
    db.add(RevisionSchedule(student_id=student.id, concept_id=cids[0], due_at=datetime.now(timezone.utc) - timedelta(hours=1), interval_days=1, reps=0))
    db.commit()
    m = mission(client, student)
    slots = [i["slot"] for i in m["items"]]
    assert slots == sorted(slots, key=["revision", "new", "challenge"].index) and "revision" in slots and "challenge" in slots
    assert all(i["reason"] and i["href"] and i["minutes"] > 0 and "evidenceCount" in i for i in m["items"])
    assert m["totalMinutes"] == sum(i["minutes"] for i in m["items"]) <= 12


def test_the_twelve_minute_cap_trims_a_long_revision_queue(db, client, student):
    cids = chapter_concepts(db)
    now = datetime.now(timezone.utc)
    for c in cids:
        db.add(ConceptState(student_id=student.id, concept_id=c, p_known=0.93, n_obs=6, n_correct=6, streak=6, status="secure", param_version="t", last_obs_at=now))
        db.add(RevisionSchedule(student_id=student.id, concept_id=c, due_at=now - timedelta(hours=1), interval_days=1, reps=0))
    db.commit()
    m = mission(client, student)
    assert 0 < m["totalMinutes"] <= 12 and all(i["minutes"] >= 1 for i in m["items"])


def test_teachers_cannot_use_the_student_mission(db, client, student):
    t = make_profile(db, "teacher")
    assert client.get(f"{API}/mission", headers=auth(t)).status_code == 403
    assert client.get(f"{API}/mission").status_code == 401


def test_map_shows_mastery_and_marks_what_unlocks_next(db, client, student):
    slug = db.scalar(select(Chapter.slug))
    ids = chapter_concepts(db)
    first = db.scalar(select(Concept).where(Concept.id.in_(ids)).order_by(Concept.grade, Concept.id))
    db.add(ConceptState(student_id=student.id, concept_id=first.id, p_known=0.95, n_obs=6, n_correct=6, streak=6, status="secure", param_version="t"))
    db.commit()
    nodes = {n["id"]: n for n in client.get(f"{API}/library/map/{slug}", headers=auth(student)).json()["nodes"]}
    assert nodes[first.id]["mastery"] == pytest.approx(0.95) and nodes[first.id]["nextUnlock"] is False       # already secure
    assert any(n["nextUnlock"] for n in nodes.values())                                                     # something is ready to learn next
    assert all(0.0 <= n["mastery"] <= 1.0 for n in nodes.values())


def test_today_carries_the_same_mission_without_a_second_request(db, client, student):
    today = client.get(f"{API}/today", headers=auth(student)).json()
    assert today["mission"] == mission(client, student)


def test_stats_endpoint_tracks_xp_and_streak_right_after_an_answer(db, client, student):
    import uuid
    from app.models import Item
    before = client.get(f"{API}/stats", headers=auth(student)).json()
    assert before["xp"]["xp"] == 0 and before["streak"]["days"] == 0 and before["todayXp"] == 0
    item = db.scalar(select(Item).where(Item.status == "published", Item.kind == "mcq"))
    r = client.post(f"{API}/evidence", headers=auth(student), json={"itemId": str(item.id), "response": {"choice": item.answer_spec["correct"]}, "hintsUsed": 0, "ms": 5000,
                                                                     "context": "solve", "clientEventId": uuid.uuid4().hex}).json()
    after = client.get(f"{API}/stats", headers=auth(student)).json()
    assert r["xp"] > 0 and after["xp"]["xp"] == r["xp"] and after["todayXp"] == r["xp"] and after["streak"]["days"] == 1
    assert after == {k: client.get(f"{API}/today", headers=auth(student)).json()[k] for k in ("xp", "streak", "todayXp")}   # one truth, two endpoints


def test_stats_is_light_and_student_only(db, client, student):
    from sqlalchemy import event
    from app.core.database import engine
    n = {"n": 0}
    hit = lambda *a: n.__setitem__("n", n["n"] + 1)
    event.listen(engine, "before_cursor_execute", hit)
    try:
        client.get(f"{API}/stats", headers=auth(student))
    finally:
        event.remove(engine, "before_cursor_execute", hit)
    assert n["n"] <= 6
    assert client.get(f"{API}/stats", headers=auth(make_profile(db, "teacher"))).status_code == 403
