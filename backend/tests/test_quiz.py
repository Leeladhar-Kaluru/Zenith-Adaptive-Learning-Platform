from datetime import timedelta

import pytest

from app.models import ClassMember, Classroom, Item, LearnerRating, QuizMatch, QuizPlayer, QuizRating
from app.services import quiz
from tests.conftest import auth, make_profile
from tests.test_api import API, world  # noqa: F401  (the published sample content)


@pytest.fixture()
def room(db, world):
    teacher = make_profile(db, "teacher")
    a, b, c = (make_profile(db, "student", grade=7, nickname=n) for n in ("Asha", "Ben", "Cara"))
    out = make_profile(db, "student", grade=7, nickname="Outsider")
    db.commit()
    cls = Classroom(teacher_id=teacher.id, name="7A", grade=7, subject_id="maths", board_id="cbse", join_code="ZEN-QZ01")
    db.add(cls)
    db.commit()
    db.add_all([ClassMember(classroom_id=cls.id, student_id=s.id) for s in (a, b, c)])
    db.commit()
    return dict(t=teacher, a=a, b=b, c=c, out=out, cls=cls, id=str(cls.id))


def join(client, room, who):
    return client.post(f"{API}/classes/{room['id']}/quiz/join", headers=auth(room[who]))


def play(client, db, room, who, mid, right=True):
    """Answer every question: the right answer when `right`, a wrong one otherwise."""
    while True:
        q = client.get(f"{API}/quiz/{mid}", headers=auth(room[who])).json().get("question")
        if not q:
            return
        item = db.get(Item, q["id"])
        spec = item.answer_spec
        if item.kind == "numeric":
            resp = {"value": spec["value"] if right else float(spec["value"]) + 999}
        elif item.kind == "truefalse":
            resp = {"choice": bool(spec["correct"]) if right else not spec["correct"]}
        else:
            resp = {"choice": spec["correct"] if right else next(o["key"] for o in item.payload["options"] if o["key"] != spec["correct"])}
        r = client.post(f"{API}/quiz/{mid}/answer", headers=auth(room[who]), json={"position": q["position"], "response": resp})
        assert r.status_code == 200


def test_two_classmates_are_matched_play_the_same_questions_and_the_server_decides_the_winner(client, db, room):
    first = join(client, room, "a").json()
    assert first["status"] == "waiting" and "opponent" not in first
    second = join(client, room, "b").json()
    assert second["status"] == "active" and second["id"] == first["id"] and second["opponent"]["nickname"] == "Asha"
    mid = first["id"]
    qa = client.get(f"{API}/quiz/{mid}", headers=auth(room["a"])).json()["question"]
    assert qa["id"] == second["question"]["id"] and "answer_spec" not in str(qa) and "'correct'" not in str(qa)       # same question, no answer leaked
    play(client, db, room, "a", mid, right=True)
    seen = client.get(f"{API}/quiz/{mid}", headers=auth(room["b"])).json()
    assert seen["status"] == "active" and seen["opponent"]["finished"] is True and seen["opponent"]["answered"] == 5
    play(client, db, room, "b", mid, right=False)
    done = client.get(f"{API}/quiz/{mid}", headers=auth(room["a"])).json()
    assert done["status"] == "done" and done["result"]["youWon"] is True and done["result"]["ratingAfter"] > done["result"]["ratingBefore"] == 1000
    assert len(done["result"]["review"]) == 5 and all(r["correct"] for r in done["result"]["review"])
    lost = client.get(f"{API}/quiz/{mid}", headers=auth(room["b"])).json()["result"]
    assert lost["youWon"] is False and lost["ratingAfter"] < 1000
    db.expire_all()
    assert abs(db.get(QuizRating, room["a"].id).rating + db.get(QuizRating, room["b"].id).rating - 2000) < 1e-6       # Elo moves points, it does not create them


def test_only_class_members_can_join_or_look_and_a_forged_answer_position_is_refused(client, db, room):
    assert client.post(f"{API}/classes/{room['id']}/quiz/join", headers=auth(room["out"])).status_code == 404
    assert client.post(f"{API}/classes/{room['id']}/quiz/join", headers=auth(room["t"])).status_code == 403          # teachers watch, they do not play
    mid = join(client, room, "a").json()["id"]
    join(client, room, "b")
    assert client.get(f"{API}/quiz/{mid}", headers=auth(room["out"])).status_code == 404
    assert client.get(f"{API}/quiz/{mid}", headers=auth(room["c"])).status_code == 404                                  # a classmate who is not in this match
    assert client.post(f"{API}/quiz/{mid}/answer", headers=auth(room["a"]), json={"position": 3, "response": {"choice": "A"}}).status_code == 409


def test_a_resent_answer_returns_the_first_result_and_is_counted_once(client, db, room):
    mid = join(client, room, "a").json()["id"]
    join(client, room, "b")
    body = {"position": 0, "response": {"choice": "Z", "value": 1}}
    first = client.post(f"{API}/quiz/{mid}/answer", headers=auth(room["a"]), json=body).json()
    again = client.post(f"{API}/quiz/{mid}/answer", headers=auth(room["a"]), json=body).json()
    assert first == again
    db.expire_all()
    assert db.get(QuizPlayer, (mid, room["a"].id)).score == first["points"]


def test_opted_out_students_and_classes_with_competition_off_cannot_play(client, db, room):
    room["a"].league_opt_out = True
    db.commit()
    assert join(client, room, "a").status_code == 403
    room["a"].league_opt_out = False
    room["cls"].leagues_enabled = False
    db.commit()
    assert join(client, room, "b").status_code == 403


def test_students_far_apart_in_rating_are_not_paired_at_first_and_nobody_plays_themselves(client, db, room):
    db.add(LearnerRating(student_id=room["a"].id, subject_id="maths", theta=2.0, n=30))
    db.commit()
    a = join(client, room, "a").json()
    assert join(client, room, "a").json()["id"] == a["id"]                                # asking again does not create a second queue entry
    b = join(client, room, "b").json()
    assert b["status"] == "waiting" and b["id"] != a["id"]                                # 2.0 apart: outside the window
    c = join(client, room, "c").json()
    assert c["status"] == "active" and c["id"] == b["id"]                                 # c is close to b


def test_leaving_a_queue_cancels_it_and_leaving_a_running_match_is_a_forfeit(client, db, room):
    q = join(client, room, "a").json()["id"]
    assert client.post(f"{API}/quiz/{q}/leave", headers=auth(room["a"])).json()["status"] == "cancelled"
    mid = join(client, room, "a").json()["id"]
    join(client, room, "b")
    res = client.post(f"{API}/quiz/{mid}/leave", headers=auth(room["a"])).json()
    assert res["status"] == "done" and res["result"]["youWon"] is False
    assert client.get(f"{API}/quiz/{mid}", headers=auth(room["b"])).json()["result"]["youWon"] is True


def test_an_expired_match_ends_with_what_was_answered_and_a_stale_queue_is_dropped(client, db, room):
    mid = join(client, room, "a").json()["id"]
    join(client, room, "b")
    m = db.get(QuizMatch, mid)
    m.deadline_at = m.deadline_at - timedelta(minutes=30)
    db.commit()
    st = client.get(f"{API}/quiz/{mid}", headers=auth(room["a"])).json()
    assert st["status"] == "done" and st["result"]["draw"] is True                        # nobody answered: 0 to 0
    w = join(client, room, "c").json()
    row = db.get(QuizMatch, w["id"])
    row.created_at = row.created_at - timedelta(seconds=quiz.WAIT_SECONDS + 5)
    db.commit()
    assert client.get(f"{API}/quiz/{w['id']}", headers=auth(room["c"])).json()["status"] == "cancelled"


def test_the_standings_show_only_nickname_avatar_and_rating(client, db, room):
    mid = join(client, room, "a").json()["id"]
    join(client, room, "b")
    play(client, db, room, "a", mid)
    play(client, db, room, "b", mid, right=False)
    url = f"{API}/classes/{room['id']}/quiz/standings"
    t = client.get(url, headers=auth(room["c"])).json()
    assert [r["nickname"] for r in t["table"]] == ["Asha", "Ben"] and set(t["table"][0]) == {"nickname", "avatar", "rating", "games", "you"}
    room["a"].league_opt_out = True
    db.commit()
    assert [r["nickname"] for r in client.get(url, headers=auth(room["c"])).json()["table"]] == ["Ben"]


def test_the_arena_lists_my_classes_my_record_and_finished_battles_with_the_opponent_as_nickname_only(client, db, room):
    empty = client.get(f"{API}/quiz/arena", headers=auth(room["a"])).json()
    assert empty["games"] == 0 and empty["recent"] == [] and [c["canPlay"] for c in empty["classes"]] == [True]
    mid = join(client, room, "a").json()["id"]
    assert client.get(f"{API}/quiz/arena", headers=auth(room["a"])).json()["classes"][0]["matchId"] == mid          # a waiting match shows so the page can resume it
    join(client, room, "b")
    play(client, db, room, "a", mid)
    play(client, db, room, "b", mid, right=False)
    arena = client.get(f"{API}/quiz/arena", headers=auth(room["a"])).json()
    assert (arena["wins"], arena["losses"], arena["draws"]) == (1, 0, 0) and arena["rating"] > 1000 and arena["classes"][0]["matchId"] is None
    battle = client.get(f"{API}/quiz/history", headers=auth(room["a"])).json()[0]
    assert battle["opponent"] == {"nickname": "Ben", "avatar": battle["opponent"]["avatar"]} and battle["youWon"] and battle["ratingAfter"] > battle["ratingBefore"]
    assert "email" not in str(battle) and battle["className"] == "7A"
    assert client.get(f"{API}/quiz/history", headers=auth(room["c"])).json() == []                                   # nobody sees battles they were not in
    assert client.get(f"{API}/quiz/arena", headers=auth(room["t"])).status_code == 403


def test_a_student_in_no_class_gets_an_honest_empty_arena(client, db, room):
    arena = client.get(f"{API}/quiz/arena", headers=auth(room["out"])).json()
    assert arena["classes"] == [] and arena["games"] == 0
