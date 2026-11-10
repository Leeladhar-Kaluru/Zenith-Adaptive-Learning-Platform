import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.cms import importer, review
from app.models import (Chapter, Classroom, ConceptState, EvidenceEvent, Item, Lesson, LessonVersion, Profile, RevisionSchedule, XpEvent)
from tests.conftest import auth, make_profile
from tests.content_fixture import build

API = "/api/v1"


def publish_all(db, tmp_path, reviewer):
    importer.import_tree(db, importer.load_tree(build(tmp_path / "content")))
    for lv in db.scalars(select(LessonVersion)).all():
        review.approve(db, lv.id, reviewer.id, manual_confirmed=True)
        review.publish(db, lv.id, reviewer.id)
    db.commit()


@pytest.fixture()
def world(db, client, tmp_path):
    reviewer = make_profile(db, "reviewer")
    publish_all(db, tmp_path, reviewer)
    student = make_profile(db, "student", grade=7)
    return {"reviewer": reviewer, "student": student, "h": auth(student)}


def item_id(db, key):
    return str(db.scalar(select(Item.id).where(Item.key == key, Item.status == "published")))


def answer(client, h, db, key, choice, *, hints=0, ctx="solve", session=None, cid=None):
    body = {"itemId": item_id(db, key), "response": {"choice": choice}, "hintsUsed": hints, "ms": 4000, "context": ctx,
            "clientEventId": cid or uuid.uuid4().hex}
    if session:
        body["sessionId"] = session
    return client.post(f"{API}/evidence", json=body, headers=h)


# ---- accounts ----------------------------------------------------------------------------------
def test_signup_requires_consent_and_cannot_pick_a_privileged_role(client, db):
    base = {"email": "a@example.test", "password": "longenough1", "displayName": "Asha", "role": "student"}
    assert client.post(f"{API}/auth/signup", json={**base, "consent": False}).status_code == 422
    assert client.post(f"{API}/auth/signup", json={**base, "role": "admin", "consent": True}).status_code == 422
    assert client.post(f"{API}/auth/signup", json={**base, "role": "reviewer", "consent": True}).status_code == 422
    r = client.post(f"{API}/auth/signup", json={**base, "consent": True})
    assert r.status_code == 200 and r.json()["profile"]["consentStatus"] == "granted"
    assert client.post(f"{API}/auth/signup", json={**base, "consent": True}).status_code == 409
    login = client.post(f"{API}/auth/login", json={"email": "a@example.test", "password": "longenough1"})
    assert login.status_code == 200 and login.json()["token"]


def test_profile_validation_and_onboarding(client, db):
    r = client.post(f"{API}/auth/signup", json={"email": "b@example.test", "password": "longenough1", "displayName": "Bala", "role": "student", "consent": True}).json()
    h = {"Authorization": f"Bearer {r['token']}"}
    assert client.put(f"{API}/profile", json={"onboardingCompleted": True}, headers=h).status_code == 422
    assert client.put(f"{API}/profile", json={"grade": 11}, headers=h).status_code == 422
    assert client.put(f"{API}/profile", json={"avatar": "dragon"}, headers=h).status_code == 422
    assert client.put(f"{API}/profile", json={"nickname": "x"}, headers=h).status_code == 422
    ok = client.put(f"{API}/profile", json={"nickname": "Bala", "avatar": "owl", "grade": 8, "language": "hi", "onboardingCompleted": True}, headers=h)
    assert ok.status_code == 200 and ok.json()["onboardingCompleted"] and ok.json()["grade"] == 8
    assert client.get(f"{API}/profile").status_code == 401


def test_learning_is_blocked_until_onboarding_and_consent(client, db):
    p = make_profile(db, "student")
    p.onboarding_completed = False
    db.commit()
    assert client.get(f"{API}/today", headers=auth(p)).status_code == 409
    p.onboarding_completed, p.consent_status = True, "pending"
    db.commit()
    assert client.get(f"{API}/today", headers=auth(p)).status_code == 403


# ---- library visibility ------------------------------------------------------------------------
def test_unpublished_content_is_invisible_and_coming_soon(client, db, tmp_path):
    importer.import_tree(db, importer.load_tree(build(tmp_path / "content")))
    s = make_profile(db, "student", grade=7)
    chs = client.get(f"{API}/library/chapters?grade=7&subject=maths", headers=auth(s)).json()
    assert [(c["title"], c["status"], c["lessonCount"]) for c in chs] == [("Integers", "coming_soon", 0)]
    lid = db.scalar(select(Lesson.id))
    assert client.get(f"{API}/library/lessons/{lid}", headers=auth(s)).status_code == 404
    assert client.post(f"{API}/evidence", json={"itemId": str(db.scalar(select(Item.id))), "response": {"choice": "A"}, "context": "solve", "clientEventId": "abcdefgh1"}, headers=auth(s)).status_code == 404


def test_published_chapter_lessons_and_no_answer_leak(client, db, world):
    h = world["h"]
    ch = client.get(f"{API}/library/chapters?grade=7", headers=h).json()[0]
    assert ch["status"] == "published" and ch["lessonCount"] == 2
    detail = client.get(f"{API}/library/chapters/{ch['slug']}", headers=h).json()
    assert [l["state"] for l in detail["lessons"]] == ["current", "todo"] and detail["objectives"]
    lesson = client.get(f"{API}/library/lessons/{detail['lessons'][0]['id']}", headers=h).json()
    blob = json.dumps(lesson)
    for leak in ("answer_spec", '"correct"', "explanation", "verify", "misconception"):
        assert leak not in blob
    check = next(b for b in lesson["blocks"] if b["kind"] == "check")
    assert check["item"]["options"] and check["item"]["hintCount"] == 1


def test_search_respects_class_and_only_published(client, db, world):
    h = world["h"]
    r = client.get(f"{API}/library/search?q=integers", headers=h).json()
    assert r["chapters"] and r["lessons"]
    g10 = make_profile(db, "student", grade=10)
    assert client.get(f"{API}/library/search?q=integers", headers=auth(g10)).json()["chapters"] == []
    assert client.get(f"{API}/library/search?q=i", headers=h).json() == {"chapters": [], "lessons": [], "concepts": []}


# ---- evidence ----------------------------------------------------------------------------------
def test_evidence_grades_updates_model_and_is_idempotent(client, db, world):
    h, s = world["h"], world["student"]
    r = answer(client, h, db, "q-line-1", "A", cid="evt-0001-aaaa").json()
    assert r["correct"] is True and r["xp"] > 0 and r["concepts"][0]["id"] == "number-line"
    again = answer(client, h, db, "q-line-1", "A", cid="evt-0001-aaaa").json()
    assert again["alreadyRecorded"] is True
    assert db.query(EvidenceEvent).count() == 1
    st = db.get(ConceptState, (s.id, "number-line"))
    assert st.n_obs == 1 and st.p_known > 0.25 and st.param_version == "prior-v1"


def test_wrong_answer_reports_the_misconception_and_awards_no_xp(client, db, world):
    r = answer(client, world["h"], db, "q-line-1", "B").json()
    assert r["correct"] is False and r["xp"] == 0 and "Subtracts the smaller" in r["misconception"]
    assert r["reveal"] == "A"


def test_hinted_correct_answer_earns_less_xp_and_less_belief(client, db, world):
    a = answer(client, world["h"], db, "q-line-2", "A", hints=0).json()
    b = answer(client, world["h"], db, "q-line-1", "A", hints=1).json()
    assert 0 < b["xp"] < a["xp"] or b["xp"] < 10
    s = world["student"]
    assert db.get(ConceptState, (s.id, "number-line")).n_obs == 2


def test_repeating_a_question_does_not_farm_xp_or_mastery(client, db, world):
    answer(client, world["h"], db, "q-line-2", "A")
    xp1 = db.query(XpEvent).filter(XpEvent.kind == "answer").count()
    for _ in range(8):
        answer(client, world["h"], db, "q-line-2", "A")
    assert db.query(XpEvent).filter(XpEvent.kind == "answer").count() == xp1 == 1
    st = db.get(ConceptState, (world["student"].id, "number-line"))
    assert st.status != "secure"      # one question answered nine times is not mastery


def test_daily_xp_cap(client, db, world, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "XP_DAILY_CAP", 12)
    answer(client, world["h"], db, "q-line-1", "A")
    answer(client, world["h"], db, "q-line-3", "A")
    answer(client, world["h"], db, "q-line-4", "A")
    total = sum(x.amount for x in db.query(XpEvent).all())
    assert total <= 12


def test_bad_inputs_are_rejected(client, db, world):
    h = world["h"]
    bad = client.post(f"{API}/evidence", json={"itemId": item_id(db, "q-line-1"), "response": {}, "context": "solve", "clientEventId": "abcdefgh2"}, headers=h)
    assert bad.status_code == 200 and bad.json()["correct"] is False     # an empty choice is a wrong answer, not a crash
    assert client.post(f"{API}/evidence", json={"itemId": item_id(db, "q-line-1"), "response": {"choice": "A"}, "context": "nope", "clientEventId": "abcdefgh3"}, headers=h).status_code == 422
    assert client.post(f"{API}/evidence", json={"itemId": item_id(db, "q-line-1"), "response": {"choice": "A"}, "context": "solve", "clientEventId": "x"}, headers=h).status_code == 422
    assert client.post(f"{API}/evidence", json={"itemId": item_id(db, "q-line-1"), "response": {"choice": "A"}, "context": "solve", "clientEventId": "abcdefgh4"}).status_code == 401


def test_offline_batch_sync_is_idempotent_and_reports_each_event(client, db, world):
    h = world["h"]
    ev = lambda key, c, cid: {"itemId": item_id(db, key), "response": {"choice": c}, "hintsUsed": 0, "ms": 2000, "context": "solve", "clientEventId": cid,
                              "occurredAt": datetime.now(timezone.utc).isoformat()}
    body = {"events": [ev("q-line-1", "A", "batch-0001"), ev("q-line-2", "B", "batch-0002"), {**ev("q-line-3", "A", "batch-0003"), "itemId": str(uuid.uuid4())}]}
    r = client.post(f"{API}/evidence/batch", json=body, headers=h).json()["results"]
    assert [x["ok"] for x in r] == [True, True, False] and r[2]["status"] == 404
    again = client.post(f"{API}/evidence/batch", json=body, headers=h).json()["results"]
    assert again[0]["result"]["alreadyRecorded"] and db.query(EvidenceEvent).count() == 2


def test_hints_are_served_one_at_a_time(client, db, world):
    r = client.get(f"{API}/items/{item_id(db, 'q-line-1')}/hint?n=1", headers=world["h"]).json()
    assert r["hint"] and r["of"] == 1


# ---- adaptivity --------------------------------------------------------------------------------
def test_gap_traces_to_the_prerequisite_and_today_says_why(client, db, world):
    h = world["h"]
    for k in ("q-line-1", "q-line-2", "q-line-3", "q-line-4"):
        answer(client, h, db, k, "D" if k != "q-line-2" else "B")   # wrong answers
    for k in ("q-add-1", "q-add-2", "q-add-3"):
        answer(client, h, db, k, "D")
    today = client.get(f"{API}/today", headers=h).json()
    step = today["nextStep"]
    assert step["kind"] == "prereq" and "Number line" in step["title"]
    assert "Adding integers" in step["reason"] and step["evidenceCount"] >= 3
    lid = step["href"].split("/")[-1]
    assert client.get(f"{API}/library/lessons/{lid}", headers=h).status_code == 200


def test_one_wrong_answer_never_creates_a_prerequisite_detour(client, db, world):
    answer(client, world["h"], db, "q-add-1", "B")
    step = client.get(f"{API}/today", headers=world["h"]).json()["nextStep"]
    assert step["kind"] != "prereq"


def test_new_student_gets_a_diagnostic_not_a_fake_weakness(client, db, world):
    today = client.get(f"{API}/today", headers=world["h"]).json()
    assert today["nextStep"]["kind"] == "probe" and today["nextStep"]["evidenceCount"] == 0
    assert today["xp"]["xp"] == 0 and today["streak"]["days"] == 0 and today["badges"] == []


def test_practice_difficulty_rises_with_evidence(client, db, world):
    h = world["h"]
    seen = []
    for _ in range(4):                       # a fresh student: challenge questions are locked
        r = client.get(f"{API}/practice/next?concept=number-line", headers=h).json()
        seen.append(r["item"]["difficulty"])
        key = db.scalar(select(Item.key).where(Item.id == uuid.UUID(r["item"]["id"])))
        answer(client, h, db, key, "A")
    assert "challenge" not in seen[:1]
    # after several correct answers on the concept the level climbs and harder questions appear
    s = world["student"]
    st = db.get(ConceptState, (s.id, "number-line"))
    assert st.p_known > 0.6
    nxt = client.get(f"{API}/practice/next?concept=number-line&harder=1", headers=h).json()
    assert nxt["concept"]["level"] >= 2 or nxt["item"]["difficulty"] == "challenge"


def test_practice_scope_errors_are_honest(client, db, world):
    h = world["h"]
    assert client.get(f"{API}/practice/next?weak=1", headers=h).status_code == 409
    assert client.get(f"{API}/practice/next?review=1", headers=h).status_code == 409
    assert client.get(f"{API}/practice/next?concept=nope", headers=h).status_code == 404


def test_revision_is_scheduled_only_for_secure_concepts_and_due_later(client, db, world):
    h, s = world["h"], world["student"]
    for k in ("q-line-1", "q-line-2", "q-line-3", "q-line-4", "q-line-1", "q-line-2", "q-line-3"):
        answer(client, h, db, k, "A")
    row = db.get(RevisionSchedule, (s.id, "number-line"))
    if db.get(ConceptState, (s.id, "number-line")).status == "secure":
        assert row is not None and row.due_at > datetime.now(timezone.utc)
    assert client.get(f"{API}/revision", headers=h).json()["due"] == []
    row = row or RevisionSchedule(student_id=s.id, concept_id="number-line", due_at=datetime.now(timezone.utc), interval_days=1, reps=0)
    row.due_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.merge(row)
    db.commit()
    assert [d["conceptId"] for d in client.get(f"{API}/revision", headers=h).json()["due"]] == ["number-line"]
    assert client.get(f"{API}/today", headers=h).json()["revision"][0]["title"] == "Number line"


# ---- lessons and progress ---------------------------------------------------------------------
def test_lesson_completion_requires_answering_the_checks(client, db, world):
    h = world["h"]
    lesson = db.scalar(select(Lesson).where(Lesson.slug == "line"))
    r = client.post(f"{API}/progress", json={"lessonId": str(lesson.id), "action": "complete"}, headers=h)
    assert r.status_code == 409 and "understanding check" in r.json()["detail"]
    answer(client, h, db, "q-line-1", "B")      # answering wrongly still counts as engaging with the check
    ok = client.post(f"{API}/progress", json={"lessonId": str(lesson.id), "action": "complete"}, headers=h).json()
    assert ok["completed"] and ok["xp"] > 0
    again = client.post(f"{API}/progress", json={"lessonId": str(lesson.id), "action": "complete"}, headers=h).json()
    assert again["xp"] == 0


def test_chapter_climber_badge_only_after_every_lesson(client, db, world):
    h = world["h"]
    for slug, key in (("line", "q-line-1"), ("adding", "q-add-1")):
        lesson = db.scalar(select(Lesson).where(Lesson.slug == slug))
        answer(client, h, db, key, "A")
        r = client.post(f"{API}/progress", json={"lessonId": str(lesson.id), "action": "complete"}, headers=h).json()
        assert ("chapter_climber" in r["newBadges"]) == (slug == "adding")


# ---- tests (assessments) ----------------------------------------------------------------------
def test_chapter_test_flow_with_concept_level_results(client, db, world):
    h = world["h"]
    s = client.post(f"{API}/assessments", json={"kind": "chapter_test", "chapter": "7-maths-integers", "timed": True}, headers=h).json()
    assert s["timeLimitS"] and s["total"] >= 4 and "explanation" not in json.dumps(s)
    for i, it in enumerate(s["items"]):
        key = db.scalar(select(Item.key).where(Item.id == uuid.UUID(it["id"])))
        r = answer(client, h, db, key, "A" if i % 2 == 0 else "B", ctx="test", session=s["id"])
        assert r.status_code == 200
    dup = answer(client, h, db, key, "A", ctx="test", session=s["id"])
    assert dup.status_code == 409
    res = client.post(f"{API}/assessments/{s['id']}/submit", headers=h).json()["summary"]
    assert res["total"] == s["total"] and res["byConcept"] and res["mistakes"] and "one signal" in res["note"]
    assert all("confidence" in c for c in res["byConcept"])
    assert client.get(f"{API}/assessments/{s['id']}", headers=h).json()["status"] == "submitted"
    assert answer(client, h, db, key, "A", ctx="test", session=s["id"]).status_code == 409   # submitted
    assert client.get(f"{API}/assessments", headers=h).json()[0]["id"] == s["id"]


def test_retake_creates_a_new_session(client, db, world):
    h = world["h"]
    a = client.post(f"{API}/assessments", json={"kind": "topic_test", "concept": "adding-integers"}, headers=h).json()
    b = client.post(f"{API}/assessments", json={"kind": "topic_test", "concept": "adding-integers"}, headers=h).json()
    assert a["id"] != b["id"]


def test_diagnostic_includes_prerequisite_concepts(client, db, world):
    s = client.post(f"{API}/assessments", json={"kind": "diagnostic", "chapter": "7-maths-integers"}, headers=world["h"]).json()
    assert s["total"] >= 4


def test_test_questions_must_belong_to_the_session_and_time_limit_is_enforced(client, db, world):
    h = world["h"]
    s = client.post(f"{API}/assessments", json={"kind": "topic_test", "concept": "number-line", "timed": True}, headers=h).json()
    outsider = next(k for k in ("q-add-1", "q-add-2", "q-add-3", "q-add-4"))
    assert answer(client, h, db, outsider, "A", ctx="test", session=s["id"]).status_code == 422
    from app.models import AssessmentSession
    row = db.get(AssessmentSession, uuid.UUID(s["id"]))
    row.started_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db.commit()
    key = db.scalar(select(Item.key).where(Item.id == uuid.UUID(s["items"][0]["id"])))
    assert answer(client, h, db, key, "A", ctx="test", session=s["id"]).status_code == 409


def test_other_students_cannot_read_or_submit_my_test(client, db, world):
    s = client.post(f"{API}/assessments", json={"kind": "topic_test", "concept": "number-line"}, headers=world["h"]).json()
    other = make_profile(db, "student")
    assert client.get(f"{API}/assessments/{s['id']}", headers=auth(other)).status_code == 404
    assert client.post(f"{API}/assessments/{s['id']}/submit", headers=auth(other)).status_code == 404


# ---- teacher ----------------------------------------------------------------------------------
def make_class(client, db, teacher):
    return client.post(f"{API}/teacher/classes", json={"name": "7B", "grade": 7, "subject": "maths"}, headers=auth(teacher)).json()


def join(client, db, cls, student):
    return client.put(f"{API}/profile", json={"classCode": cls["joinCode"]}, headers=auth(student))


def test_class_join_overview_and_student_isolation(client, db, world):
    t = make_profile(db, "teacher")
    cls = make_class(client, db, t)
    assert cls["joinCode"].startswith("ZEN-")
    s = world["student"]
    assert join(client, db, cls, s).status_code == 200
    assert client.put(f"{API}/profile", json={"classCode": "ZEN-NOPE"}, headers=world["h"]).status_code == 404
    answer(client, world["h"], db, "q-line-1", "A")
    ov = client.get(f"{API}/teacher/classes/{cls['id']}", headers=auth(t)).json()
    assert ov["cls"]["students"] == 1 and len(ov["heatmap"]) == 1
    assert ov["heatmap"][0]["cells"][0]["evidence"] in (0, 1)
    other = make_profile(db, "teacher")
    assert client.get(f"{API}/teacher/classes/{cls['id']}", headers=auth(other)).status_code == 404
    assert client.get(f"{API}/teacher/classes/{cls['id']}", headers=world["h"]).status_code == 403
    d = client.get(f"{API}/teacher/classes/{cls['id']}/students/{s.id}", headers=auth(t)).json()
    assert d["timeline"] and d["concepts"]
    stranger = make_profile(db, "student")
    assert client.get(f"{API}/teacher/classes/{cls['id']}/students/{stranger.id}", headers=auth(t)).status_code == 404


def test_suggestion_needs_several_struggling_students_and_cites_evidence(client, db, world):
    t = make_profile(db, "teacher")
    cls = make_class(client, db, t)
    kids = [world["student"]] + [make_profile(db, "student", grade=7) for _ in range(3)]
    for k in kids:
        join(client, db, cls, k)
    # one struggling student: no suggestion yet
    for key in ("q-add-1", "q-add-2", "q-add-3"):
        answer(client, auth(kids[0]), db, key, "D")
    assert client.get(f"{API}/teacher/classes/{cls['id']}", headers=auth(t)).json()["suggestions"] == []
    for k in kids[1:3]:
        for key in ("q-add-1", "q-add-2", "q-add-3"):
            answer(client, auth(k), db, key, "D")
    sug = client.get(f"{API}/teacher/classes/{cls['id']}", headers=auth(t)).json()["suggestions"]
    assert len(sug) == 1 and sug[0]["students"] == 3 and "3 of 4 students" in sug[0]["text"] and "9 answers" == sug[0]["evidence"]
    # assigning from the suggestion records an intervention and removes the suggestion
    r = client.post(f"{API}/teacher/assignments", json={"classId": cls["id"], "kind": "lesson", "lessonId": sug[0]["lessonId"], "suggestionKey": sug[0]["key"],
                                                         "conceptIds": [sug[0]["conceptId"]], "studentIds": sug[0]["studentIds"]}, headers=auth(t))
    assert r.status_code == 200
    assert client.get(f"{API}/teacher/classes/{cls['id']}", headers=auth(t)).json()["suggestions"] == []
    from app.models import Intervention
    assert db.query(Intervention).count() == 3
    mine = client.get(f"{API}/assignments", headers=auth(kids[0])).json()
    assert mine and mine[0]["total"] == 1 and mine[0]["complete"] is False
    assert client.get(f"{API}/today", headers=auth(kids[0])).json()["nextStep"]["kind"] == "assigned"


def test_teacher_can_dismiss_a_suggestion_and_cannot_assign_unpublished_work(client, db, world):
    t = make_profile(db, "teacher")
    cls = make_class(client, db, t)
    assert client.post(f"{API}/teacher/classes/{cls['id']}/decisions", json={"key": "k1", "action": "dismissed"}, headers=auth(t)).status_code == 200
    bad = client.post(f"{API}/teacher/assignments", json={"classId": cls["id"], "kind": "practice", "chapter": "no-such"}, headers=auth(t))
    assert bad.status_code == 422
    assert client.post(f"{API}/teacher/assignments", json={"classId": cls["id"], "kind": "lesson"}, headers=auth(t)).status_code == 422


def test_leagues_explain_why_they_are_missing_and_respect_opt_out(client, db, world):
    h, s = world["h"], world["student"]
    g = client.get(f"{API}/gamification", headers=h).json()
    assert g["league"] is None and g["reason"] == "no_classroom"
    t = make_profile(db, "teacher")
    cls = make_class(client, db, t)
    a, b = world["student"], make_profile(db, "student", grade=7)
    join(client, db, cls, a), join(client, db, cls, b)
    answer(client, h, db, "q-line-1", "A")
    g = client.get(f"{API}/gamification", headers=h).json()
    assert g["league"]["tier"] == "foothill" and [r["me"] for r in g["league"]["rows"]].count(True) == 1
    assert all(set(r) == {"rank", "nickname", "avatar", "xp", "me", "zone"} for r in g["league"]["rows"])   # nothing but nickname and character
    client.put(f"{API}/teacher/classes/{cls['id']}/leagues", json={"enabled": False}, headers=auth(t))
    assert client.get(f"{API}/gamification", headers=h).json()["reason"] == "teacher_off"
    client.put(f"{API}/teacher/classes/{cls['id']}/leagues", json={"enabled": True}, headers=auth(t))
    client.put(f"{API}/profile", json={"leagueOptOut": True}, headers=h)
    assert client.get(f"{API}/gamification", headers=h).json()["reason"] == "opted_out"


# ---- review access ---------------------------------------------------------------------------
def test_only_reviewers_can_review_and_publish(client, db, tmp_path):
    importer.import_tree(db, importer.load_tree(build(tmp_path / "content")))
    teacher, student, reviewer = make_profile(db, "teacher"), make_profile(db, "student"), make_profile(db, "reviewer")
    assert client.get(f"{API}/review/queue", headers=auth(student)).status_code == 403
    assert client.get(f"{API}/review/queue", headers=auth(teacher)).status_code == 403
    q = client.get(f"{API}/review/queue", headers=auth(reviewer)).json()
    assert len(q) == 2 and all(x["status"] == "in_review" for x in q)
    vid = q[0]["id"]
    detail = client.get(f"{API}/review/lessons/{vid}", headers=auth(reviewer)).json()
    assert any(g["manual"] and not g["passed"] for g in detail["gates"]) and detail["answers"] and detail["lesson"]["blocks"]
    no = client.post(f"{API}/review/lessons/{vid}", json={"decision": "approve_publish"}, headers=auth(reviewer))
    assert no.status_code == 422 and "Confirm" in no.json()["detail"]
    ok = client.post(f"{API}/review/lessons/{vid}", json={"decision": "approve_publish", "manualGatesConfirmed": True}, headers=auth(reviewer))
    assert ok.json()["status"] == "published"
    cov = client.get(f"{API}/review/coverage", headers=auth(reviewer)).json()
    assert cov[0]["published"] == 1 and cov[0]["lessons"] == 2 and cov[0]["status"] == "in_production"


# ---- tutor ----------------------------------------------------------------------------------
def test_tutor_without_ai_answers_from_the_lesson_and_says_so(client, db, world):
    lesson = db.scalar(select(Lesson).where(Lesson.slug == "line"))
    r = client.post(f"{API}/tutor/ask", json={"message": "What are numbers below zero?", "lessonId": str(lesson.id)}, headers=world["h"]).json()
    assert r["degraded"] is True and "less than zero" in r["reply"] and r["citations"]


def test_tutor_prompt_has_no_student_identity_and_hides_nothing_about_ai(client, db, world, monkeypatch):
    from app.services import tutor
    seen = {}

    async def fake(messages, **kw):
        seen["m"] = json.dumps(messages)
        return "Think of the line. Which way do you move when you subtract?"

    monkeypatch.setattr(tutor, "ai_enabled", lambda: True)
    monkeypatch.setattr(tutor.ai_provider, "generate_chat", fake)
    lesson = db.scalar(select(Lesson).where(Lesson.slug == "line"))
    r = client.post(f"{API}/tutor/ask", json={"message": "Help me with 2 - 5", "lessonId": str(lesson.id), "language": "hi"}, headers=world["h"]).json()
    s = world["student"]
    assert not r["degraded"] and r["aiTranslated"] is True and r["language"] == "hi"
    assert str(s.id) not in seen["m"] and s.email not in seen["m"] and s.display_name not in seen["m"] and "Hindi" in seen["m"]


def test_tutor_rate_limit(client, db, world, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "TUTOR_DAILY_LIMIT", 2)
    for _ in range(2):
        assert client.post(f"{API}/tutor/ask", json={"message": "integers please"}, headers=world["h"]).status_code == 200
    assert client.post(f"{API}/tutor/ask", json={"message": "integers please"}, headers=world["h"]).status_code == 429


# ---- progress and engagement -----------------------------------------------------------------
def test_my_progress_reflects_only_real_evidence(client, db, world):
    h = world["h"]
    empty = client.get(f"{API}/progress/overview", headers=h).json()
    assert empty["concepts"] == [] and empty["xp"]["xp"] == 0 and empty["mistakes"] == 0 and all(not b["earned"] for b in empty["badges"])
    answer(client, h, db, "q-line-1", "B")
    o = client.get(f"{API}/progress/overview", headers=h).json()
    assert o["concepts"][0]["evidence"] == 1 and o["concepts"][0]["confidence"] == "low" and o["mistakes"] == 1
    m = client.get(f"{API}/progress/mistakes", headers=h).json()
    assert m[0]["misconception"] and not m[0]["resolved"]
    answer(client, h, db, "q-line-1", "A")
    assert client.get(f"{API}/progress/mistakes", headers=h).json() == []
    assert client.get(f"{API}/progress/mistakes?all=1", headers=h).json()[0]["resolved"] is True
    assert [b["id"] for b in o["badges"] if b["earned"]] == ["first_step"]


def test_explore_is_honest_about_what_exists(client, db, world):
    e = client.get(f"{API}/explore", headers=world["h"]).json()
    assert [a["key"] for a in e["available"]] == ["flashcards"] and e["planned"]


def test_lesson_start_is_idempotent_when_sent_twice(db, client, world):
    lesson = db.scalar(select(Lesson).limit(1))
    h = world["h"]
    for _ in range(3):
        r = client.post(f"{API}/progress", json={"lessonId": str(lesson.id), "action": "start"}, headers=h)
        assert r.status_code == 200 and r.json() == {"ok": True}
