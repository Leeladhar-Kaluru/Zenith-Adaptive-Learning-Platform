from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Assignment, ClassMember, Classroom, Profile
from tests.conftest import auth, make_profile

API = "/api/v1"


def make_class(db, teacher, name="7A Maths", grade=7, code=None):
    c = Classroom(teacher_id=teacher.id, name=name, grade=grade, subject_id="maths", board_id="cbse", join_code=code or f"ZEN-{name[:2].upper()}{grade}X")
    db.add(c)
    db.commit()
    return c


def join(db, student, cls, status="active"):
    db.add(ClassMember(classroom_id=cls.id, student_id=student.id, status=status))
    db.commit()


@pytest.fixture()
def world(db):
    teacher = make_profile(db, "teacher", display_name="Ms Rao") if False else make_profile(db, "teacher")
    teacher.display_name = "Ms Rao"
    other_teacher = make_profile(db, "teacher")
    a, b = make_profile(db, "student", nickname="Asha"), make_profile(db, "student", nickname="Ben")
    private = make_profile(db, "student", nickname="Hidden")
    private.league_opt_out = True
    db.commit()
    mine, theirs = make_class(db, teacher, "7A Maths"), make_class(db, other_teacher, "8B Science", 8)
    for s in (a, b, private):
        join(db, s, mine)
    join(db, b, theirs)
    return dict(teacher=teacher, other=other_teacher, a=a, b=b, private=private, mine=mine, theirs=theirs)


def test_a_student_sees_only_the_classes_they_belong_to(db, client, world):
    rows = client.get(f"{API}/classes", headers=auth(world["a"])).json()
    assert [r["id"] for r in rows] == [str(world["mine"].id)]
    r = rows[0]
    assert r["teacher"]["name"] == "Ms Rao" and r["subject"] == "maths" and r["grade"] == 7 and r["classmates"] == 3
    both = client.get(f"{API}/classes", headers=auth(world["b"])).json()
    assert {x["id"] for x in both} == {str(world["mine"].id), str(world["theirs"].id)}


def test_a_class_you_are_not_in_looks_like_it_does_not_exist(db, client, world):
    assert client.get(f"{API}/classes/{world['theirs'].id}", headers=auth(world["a"])).status_code == 404
    assert client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["other"])).status_code == 404       # another teacher
    assert client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["teacher"])).status_code == 200      # the owner


def test_classmates_are_shown_by_nickname_and_avatar_only(db, client, world):
    body = client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["a"])).json()
    names = sorted(m["nickname"] for m in body["classmates"])
    assert names == ["A classmate", "Asha", "Ben"]                       # the opted-out student is not named
    flat = str(body["classmates"])
    for p in (world["a"], world["b"], world["private"]):
        assert p.email not in flat and str(p.id) not in flat and p.display_name not in flat or p.display_name == "Test User" and "Test User" not in flat
    assert [m["me"] for m in body["classmates"] if m["nickname"] == "Asha"] == [True]
    assert set(body["classmates"][0]) == {"nickname", "avatar", "me"}


def test_leaving_removes_access_keeps_history_and_rejoining_works(db, client, world):
    r = client.delete(f"{API}/classes/{world['mine'].id}/membership", headers=auth(world["a"]))
    assert r.status_code == 200
    assert client.get(f"{API}/classes", headers=auth(world["a"])).json() == []
    assert client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["a"])).status_code == 404
    row = db.get(ClassMember, (world["mine"].id, world["a"].id))
    assert row is not None and row.status == "left"                       # the record stays; only access ends
    assert client.delete(f"{API}/classes/{world['mine'].id}/membership", headers=auth(world["a"])).status_code == 404   # already left
    ok = client.put(f"{API}/profile", headers=auth(world["a"]), json={"classCode": world["mine"].join_code})
    assert ok.status_code == 200
    assert [x["id"] for x in client.get(f"{API}/classes", headers=auth(world["a"])).json()] == [str(world["mine"].id)]


def test_a_teacher_cannot_leave_through_the_student_endpoint(db, client, world):
    assert client.delete(f"{API}/classes/{world['mine'].id}/membership", headers=auth(world["teacher"])).status_code == 403


def test_upcoming_activities_are_ordered_by_due_date_and_scoped_to_the_class(db, client, world):
    now = datetime.now(timezone.utc)
    soon = Assignment(classroom_id=world["mine"].id, kind="practice", concept_ids=["x"], title="Practice fractions", due_at=now + timedelta(days=1), created_by=world["teacher"].id)
    later = Assignment(classroom_id=world["mine"].id, kind="lesson", concept_ids=[], title="Read lesson", due_at=now + timedelta(days=5), created_by=world["teacher"].id)
    other = Assignment(classroom_id=world["theirs"].id, kind="practice", concept_ids=["x"], title="Other class work", due_at=now, created_by=world["other"].id)
    db.add_all([later, soon, other])
    db.commit()
    body = client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["a"])).json()
    assert [x["title"] for x in body["assignments"]] == ["Practice fractions", "Read lesson"]
    assert client.get(f"{API}/classes", headers=auth(world["a"])).json()[0]["nextDue"]["title"] == "Practice fractions"


def test_teachers_post_announcements_and_students_read_them_pinned_first(db, client, world):
    t = auth(world["teacher"])
    first = client.post(f"{API}/classes/{world['mine'].id}/announcements", headers=t, json={"title": "Test on Friday", "body": "Chapter 2 only."})
    assert first.status_code == 200
    second = client.post(f"{API}/classes/{world['mine'].id}/announcements", headers=t, json={"title": "Bring a ruler", "body": "For geometry.", "pinned": True}).json()
    body = client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["a"])).json()
    assert [x["title"] for x in body["announcements"]] == ["Bring a ruler", "Test on Friday"] and body["announcements"][0]["pinned"] is True
    assert body["announcements"][0]["author"] == "Ms Rao"
    unpin = client.put(f"{API}/classes/{world['mine'].id}/announcements/{second['id']}/pin", headers=t, json={"pinned": False})
    assert unpin.status_code == 200
    again = client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["a"])).json()["announcements"]
    assert [x["title"] for x in again] == ["Bring a ruler", "Test on Friday"] and not any(x["pinned"] for x in again)      # newest first once unpinned
    assert client.delete(f"{API}/classes/{world['mine'].id}/announcements/{second['id']}", headers=t).status_code == 200
    assert [x["title"] for x in client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["a"])).json()["announcements"]] == ["Test on Friday"]


def test_only_the_owning_teacher_can_post_and_content_is_validated(db, client, world):
    url = f"{API}/classes/{world['mine'].id}/announcements"
    assert client.post(url, headers=auth(world["a"]), json={"title": "hi", "body": "x"}).status_code == 403          # students cannot
    assert client.post(url, headers=auth(world["other"]), json={"title": "hi", "body": "x"}).status_code == 404       # another teacher cannot
    t = auth(world["teacher"])
    assert client.post(url, headers=t, json={"title": "  ", "body": "x"}).status_code == 422
    assert client.post(url, headers=t, json={"title": "ok", "body": "x" * 4001}).status_code == 422
    assert client.post(url, headers=t, json={"title": "x" * 121, "body": "ok"}).status_code == 422
    ann = client.post(url, headers=t, json={"title": "<b>Hi</b>", "body": "<script>1</script>text"}).json()
    got = client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["a"])).json()["announcements"][0]
    assert "<" not in got["title"] and "<script" not in got["body"] and "text" in got["body"] and ann["id"]
    assert client.delete(f"{url}/{ann['id']}", headers=auth(world["other"])).status_code == 404
    assert client.delete(f"{url}/{ann['id']}", headers=auth(world["a"])).status_code == 403


def test_a_student_who_left_cannot_read_announcements(db, client, world):
    client.post(f"{API}/classes/{world['mine'].id}/announcements", headers=auth(world["teacher"]), json={"title": "Secret plan", "body": "hush"})
    client.delete(f"{API}/classes/{world['mine'].id}/membership", headers=auth(world["a"]))
    assert client.get(f"{API}/classes/{world['mine'].id}", headers=auth(world["a"])).status_code == 404
