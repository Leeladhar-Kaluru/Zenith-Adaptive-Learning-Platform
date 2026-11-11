import pytest

from app.models import ChatMessage, ClassMember, Classroom
from app.services import chatfiles
from tests.conftest import auth, make_profile

API = "/api/v1"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"0" * 64


@pytest.fixture()
def room(db):
    teacher = make_profile(db, "teacher")
    teacher.display_name = "Ms Rao"
    other = make_profile(db, "teacher")
    a, b, c = (make_profile(db, "student", nickname=n) for n in ("Asha", "Ben", "Cara"))
    outsider = make_profile(db, "student", nickname="Outsider")
    db.commit()
    cls = Classroom(teacher_id=teacher.id, name="7A", grade=7, subject_id="maths", board_id="cbse", join_code="ZEN-CHT1")
    db.add(cls)
    db.commit()
    db.add_all([ClassMember(classroom_id=cls.id, student_id=s.id) for s in (a, b, c)])
    db.commit()
    return dict(t=teacher, other=other, a=a, b=b, c=c, out=outsider, id=str(cls.id), base=f"{API}/classes/{cls.id}/chat")


@pytest.fixture()
def store(monkeypatch):
    saved = {}
    monkeypatch.setattr(chatfiles, "put", lambda key, data, mime: saved.__setitem__(key, (data, mime)))
    monkeypatch.setattr(chatfiles, "signed_url", lambda key: f"https://files.test/{key}?Authorization=tmp")
    return saved


def say(client, room, who, text, **kw):
    return client.post(f"{room['base']}/messages", headers=auth(room[who]), json={"text": text, **kw})


def test_only_class_members_can_read_or_write_and_non_members_get_404(client, room):
    assert say(client, room, "a", "Hello class").status_code == 200
    for who in ("out", "other"):
        assert client.get(room["base"], headers=auth(room[who])).status_code == 404
        assert say(client, room, who, "let me in").status_code == 404
    assert client.get(room["base"], headers=auth(room["t"])).status_code == 200      # the owning teacher


def test_messages_come_back_oldest_first_with_paging(client, room, db):
    for i in range(7):
        say(client, room, "a", f"msg {i}")
        db.query(ChatMessage).filter(ChatMessage.body == f"msg {i}").update({"created_at": ChatMessage.created_at + __import__("datetime").timedelta(seconds=i)})
        db.commit()
    page = client.get(f"{room['base']}?limit=3", headers=auth(room["b"])).json()
    assert [m["body"] for m in page["messages"]] == ["msg 4", "msg 5", "msg 6"] and page["hasMore"] and page["next"]
    older = client.get(room["base"], headers=auth(room["b"]), params={"limit": 3, "before": page["next"]}).json()
    assert [m["body"] for m in older["messages"]] == ["msg 1", "msg 2", "msg 3"]


def test_authors_show_nickname_and_avatar_never_ids_or_emails(client, room):
    say(client, room, "a", "hi")
    say(client, room, "t", "welcome")
    body = client.get(room["base"], headers=auth(room["b"])).json()
    flat = str(body)
    for p in (room["a"], room["b"], room["t"]):
        assert p.email not in flat and str(p.id) not in flat
    by = {m["body"]: m["author"] for m in body["messages"]}
    assert by["hi"] == {"nickname": "Asha", "avatar": "fox", "teacher": False, "me": False} and by["welcome"]["nickname"] == "Ms Rao" and by["welcome"]["teacher"]


@pytest.mark.parametrize("text", ["see https://evil.example/x", "go to www.bad.com", "mail me a@b.com", "call 98765 43210", "visit chat.gg", "you idiot"])
def test_unsafe_messages_are_refused_for_students(client, room, text):
    r = say(client, room, "a", text)
    assert r.status_code == 422 and r.json()["detail"]
    assert client.get(room["base"], headers=auth(room["b"])).json()["messages"] == []


@pytest.mark.parametrize("text", ["Sexual reproduction in plants uses flowers", "pi is 3.14159265358979", "the answer is 42", "Is 12.5 cm right?", "Use x.y notation"])
def test_ordinary_school_talk_is_allowed(client, room, text):
    assert say(client, room, "a", text).status_code == 200


def test_the_teacher_can_share_links_and_students_cannot_post_html(client, room):
    assert say(client, room, "t", "Worksheet: https://school.example/w").status_code == 200
    r = say(client, room, "a", "<script>x()</script>safe <b>text</b>")
    assert r.json()["body"] == "safe text"
    assert say(client, room, "a", "   ").status_code == 422
    assert say(client, room, "a", "x" * 1001).status_code == 422


def test_replies_and_threads(client, room):
    root = say(client, room, "a", "What is 3/4 + 1/4?").json()
    r1 = say(client, room, "b", "It is 1", replyTo=root["id"]).json()
    r2 = say(client, room, "c", "Agree with Ben", replyTo=r1["id"]).json()
    assert r1["replyTo"]["nickname"] == "Asha" and r2["parentId"] == root["id"]            # nested replies stay in the root's thread
    top = client.get(room["base"], headers=auth(room["a"])).json()["messages"]
    assert [m["body"] for m in top] == ["What is 3/4 + 1/4?"] and top[0]["threadCount"] == 2
    th = client.get(f"{room['base']}/messages/{root['id']}/thread", headers=auth(room["a"])).json()
    assert [m["body"] for m in th["messages"]] == ["It is 1", "Agree with Ben"] and th["root"]["body"].startswith("What is")


def test_reactions_toggle_use_a_fixed_set_and_count(client, room):
    m = say(client, room, "a", "great").json()
    url = f"{room['base']}/messages/{m['id']}/reaction"
    assert client.put(url, headers=auth(room["b"]), json={"emoji": "👍"}).json()["reactions"] == [{"emoji": "👍", "count": 1, "mine": True}]
    two = client.put(url, headers=auth(room["c"]), json={"emoji": "👍"}).json()
    assert two["reactions"] == [{"emoji": "👍", "count": 2, "mine": True}]
    seen = client.get(room["base"], headers=auth(room["a"])).json()["messages"][0]["reactions"]
    assert seen == [{"emoji": "👍", "count": 2, "mine": False}]
    assert client.put(url, headers=auth(room["b"]), json={"emoji": "👍"}).json()["reactions"][0]["count"] == 1     # toggled off
    assert client.put(url, headers=auth(room["b"]), json={"emoji": "💀"}).status_code == 422
    assert client.put(f"{room['base']}/messages/{m['id']}/reaction", headers=auth(room["out"]), json={"emoji": "👍"}).status_code == 404


def test_only_the_teacher_posts_polls_and_announcements_and_students_vote_once(client, room):
    body = {"question": "Test day?", "options": ["Thursday", "Friday"]}
    assert client.post(f"{room['base']}/polls", headers=auth(room["a"]), json=body).status_code == 403
    assert say(client, room, "a", "Notice!", announcement=True).status_code == 403
    assert say(client, room, "t", "Test on Friday", announcement=True).json()["kind"] == "announcement"
    poll = client.post(f"{room['base']}/polls", headers=auth(room["t"]), json=body).json()
    assert poll["poll"]["options"] == [{"text": "Thursday", "votes": 0}, {"text": "Friday", "votes": 0}]
    v = f"{room['base']}/messages/{poll['id']}/vote"
    client.put(v, headers=auth(room["a"]), json={"option": 1})
    client.put(v, headers=auth(room["b"]), json={"option": 1})
    changed = client.put(v, headers=auth(room["a"]), json={"option": 0}).json()["poll"]
    assert changed["total"] == 2 and [o["votes"] for o in changed["options"]] == [1, 1] and changed["myVote"] == 0
    assert client.put(v, headers=auth(room["a"]), json={"option": 5}).status_code == 422
    assert client.post(f"{room['base']}/polls", headers=auth(room["t"]), json={"question": "q", "options": ["only one"]}).status_code == 422


def test_pinning_is_teacher_only_and_deleting_follows_ownership(client, room):
    m = say(client, room, "a", "Remember the ruler").json()
    pin = f"{room['base']}/messages/{m['id']}/pin"
    assert client.put(pin, headers=auth(room["a"]), json={"pinned": True}).status_code == 403
    assert client.put(pin, headers=auth(room["t"]), json={"pinned": True}).status_code == 200
    assert [x["body"] for x in client.get(room["base"], headers=auth(room["b"])).json()["pinned"]] == ["Remember the ruler"]
    other = say(client, room, "b", "mine").json()
    assert client.delete(f"{room['base']}/messages/{other['id']}", headers=auth(room["a"])).status_code == 403     # not yours
    assert client.delete(f"{room['base']}/messages/{other['id']}", headers=auth(room["b"])).status_code == 200
    assert client.delete(f"{room['base']}/messages/{m['id']}", headers=auth(room["t"])).status_code == 200        # teacher moderates
    got = {x["id"]: x for x in client.get(room["base"], headers=auth(room["c"])).json()["messages"]}
    assert got[other["id"]]["removed"] and got[other["id"]]["body"] == "This message was removed."
    assert client.get(room["base"], headers=auth(room["c"])).json()["pinned"] == []


def test_search_finds_messages_and_treats_wildcards_as_text(client, room):
    for t in ("Fractions are fun", "100% sure", "Decimals too"):
        say(client, room, "a", t)
    hit = client.get(room["base"], headers=auth(room["b"]), params={"q": "fraction"}).json()["messages"]
    assert [m["body"] for m in hit] == ["Fractions are fun"]
    pct = client.get(room["base"], headers=auth(room["b"]), params={"q": "%"}).json()["messages"]
    assert [m["body"] for m in pct] == ["100% sure"]                    # "%" is not a wildcard


def test_unread_counts_follow_read_marks(client, room):
    say(client, room, "a", "one")
    say(client, room, "c", "two")
    assert client.get(f"{room['base']}/unread", headers=auth(room["b"])).json() == {"unread": 2}
    assert client.get(f"{API}/classes", headers=auth(room["b"])).json()[0]["unread"] == 2
    assert client.get(f"{room['base']}/unread", headers=auth(room["a"])).json() == {"unread": 1}                  # your own messages never count
    client.post(f"{room['base']}/read", headers=auth(room["b"]))
    assert client.get(f"{room['base']}/unread", headers=auth(room["b"])).json() == {"unread": 0}
    say(client, room, "a", "three")
    assert client.get(f"{room['base']}/unread", headers=auth(room["b"])).json() == {"unread": 1}


def test_reporting_reaches_the_teacher_who_can_remove_and_mute(client, room):
    bad = say(client, room, "a", "you are slow").json()
    url = f"{room['base']}/messages/{bad['id']}/report"
    assert client.post(url, headers=auth(room["a"]), json={"reason": "x"}).status_code == 422           # not your own
    assert client.post(url, headers=auth(room["b"]), json={"reason": "Unkind to me"}).status_code == 200
    client.post(url, headers=auth(room["b"]), json={"reason": "again"})                                    # duplicates ignored
    assert client.get(f"{room['base']}/reports", headers=auth(room["b"])).status_code == 403
    rep = client.get(f"{room['base']}/reports", headers=auth(room["t"])).json()
    assert len(rep) == 1 and rep[0]["reason"] == "Unkind to me" and rep[0]["message"]["body"] == "you are slow"
    assert client.post(f"{room['base']}/reports/{rep[0]['id']}/resolve", headers=auth(room["t"]), json={"deleteMessage": True, "muteMinutes": 30}).status_code == 200
    assert client.get(f"{room['base']}/reports", headers=auth(room["t"])).json() == []
    assert say(client, room, "a", "sorry").status_code == 403                                              # muted
    page = client.get(room["base"], headers=auth(room["a"])).json()
    assert page["muted"] is True and page["messages"][0]["removed"]


def test_teacher_can_mute_and_unmute_from_a_message(client, room):
    m = say(client, room, "b", "hello").json()
    assert client.post(f"{room['base']}/messages/{m['id']}/mute", headers=auth(room["a"]), json={"minutes": 10}).status_code == 403
    assert client.post(f"{room['base']}/messages/{m['id']}/mute", headers=auth(room["t"]), json={"minutes": 10}).status_code == 200
    assert say(client, room, "b", "again").status_code == 403
    assert say(client, room, "a", "I can still talk").status_code == 200
    assert client.delete(f"{room['base']}/messages/{m['id']}/mute", headers=auth(room["t"])).status_code == 200
    assert say(client, room, "b", "back").status_code == 200


def test_blocking_hides_a_classmate_for_me_only_and_can_be_undone(client, room):
    m = say(client, room, "a", "tease").json()
    say(client, room, "c", "visible to all")
    assert client.post(f"{room['base']}/messages/{m['id']}/block", headers=auth(room["b"])).status_code == 200
    assert [x["body"] for x in client.get(room["base"], headers=auth(room["b"])).json()["messages"]] == ["visible to all"]
    assert len(client.get(room["base"], headers=auth(room["c"])).json()["messages"]) == 2                       # others still see it
    mine = client.get(f"{API}/chat/blocks", headers=auth(room["b"])).json()
    assert [x["nickname"] for x in mine] == ["Asha"] and client.get(f"{API}/chat/blocks", headers=auth(room["c"])).json() == []
    assert client.delete(f"{API}/chat/blocks/{mine[0]['id']}", headers=auth(room["c"])).status_code == 404       # not yours to lift
    assert client.delete(f"{API}/chat/blocks/{mine[0]['id']}", headers=auth(room["b"])).status_code == 200
    assert len(client.get(room["base"], headers=auth(room["b"])).json()["messages"]) == 2
    t = say(client, room, "t", "hi all").json()
    assert client.post(f"{room['base']}/messages/{t['id']}/block", headers=auth(room["b"])).status_code == 422     # a teacher cannot be blocked


def test_a_burst_of_messages_is_slowed_down(client, room):
    codes = [say(client, room, "a", f"spam {i}").status_code for i in range(10)]
    assert codes[:8] == [200] * 8 and 429 in codes[8:]


def test_students_who_left_lose_access(client, room):
    client.delete(f"{API}/classes/{room['id']}/membership", headers=auth(room["a"]))
    assert client.get(room["base"], headers=auth(room["a"])).status_code == 404
    assert say(client, room, "a", "hello?").status_code == 404


def test_uploads_are_checked_by_content_size_and_stored_privately(client, room, store):
    up = f"{room['base']}/upload"
    img = client.post(up, headers=auth(room["a"]), params={"name": "../../evil name.exe", "caption": "my diagram"}, content=PNG)
    assert img.status_code == 200
    j = img.json()
    assert j["kind"] == "image" and j["attachment"]["name"] == "evil name.png" and j["attachment"]["type"] == "image/png" and j["body"] == "my diagram"
    key = next(iter(store))
    assert key.startswith(f"classchat/{room['id']}/") and key.endswith(".png") and "key" not in str(j)           # the storage key never reaches browsers
    assert client.post(up, headers=auth(room["a"]), params={"name": "notes.pdf"}, content=PDF).json()["kind"] == "file"
    assert client.post(up, headers=auth(room["a"]), params={"name": "run.png"}, content=b"MZ\x90\x00 not an image").status_code == 422     # name lies, bytes do not
    assert client.post(up, headers=auth(room["a"]), params={"name": "big.png"}, content=PNG + b"0" * (chatfiles.MAX_BYTES + 1)).status_code == 413
    assert client.post(up, headers=auth(room["a"]), params={"name": "x.png"}, content=b"").status_code == 422
    assert client.post(up, headers=auth(room["out"]), params={"name": "x.png"}, content=PNG).status_code == 404
    assert client.post(up, headers=auth(room["a"]), params={"name": "x.png", "caption": "mail a@b.com"}, content=PNG).status_code == 422


def test_file_links_are_short_lived_and_only_for_class_members(client, room, store):
    j = client.post(f"{room['base']}/upload", headers=auth(room["a"]), params={"name": "d.png"}, content=PNG).json()
    link = f"{room['base']}/messages/{j['id']}/file"
    got = client.get(link, headers=auth(room["b"])).json()
    assert got["url"].startswith("https://files.test/classchat/") and got["expiresIn"] == chatfiles.LINK_SECONDS and got["name"] == "d.png"
    assert client.get(link, headers=auth(room["out"])).status_code == 404
    text = say(client, room, "a", "no file here").json()
    assert client.get(f"{room['base']}/messages/{text['id']}/file", headers=auth(room["b"])).status_code == 404
    client.delete(f"{room['base']}/messages/{j['id']}", headers=auth(room["a"]))
    assert client.get(link, headers=auth(room["b"])).status_code == 404                                         # removed files stop being served


def test_gifs_only_from_the_provider_and_search_is_off_without_a_key(client, room, monkeypatch):
    good = "https://media1.giphy.com/media/abc/200.gif"
    assert client.post(f"{room['base']}/gifs", headers=auth(room["a"]), json={"url": good, "title": "cheer"}).json()["kind"] == "gif"
    for bad in ("https://evil.example/t.gif", "http://media.giphy.com/x.gif", "https://media.giphy.com.evil.example/x.gif", "javascript:alert(1)"):
        assert client.post(f"{room['base']}/gifs", headers=auth(room["a"]), json={"url": bad}).status_code == 422
    monkeypatch.setattr("app.services.chatfiles.settings.GIPHY_API_KEY", None)
    assert client.get(f"{room['base']}/gifs", headers=auth(room["a"]), params={"q": "cat"}).status_code == 503
    monkeypatch.setattr(chatfiles, "gif_search", lambda q, limit=12: [{"id": "1", "title": q, "url": good, "preview": good}])
    r = client.get(f"{room['base']}/gifs", headers=auth(room["a"]), params={"q": "cat"}).json()
    assert r["gifs"][0]["url"] == good and r["credit"] == "Powered by GIPHY"
    assert client.get(f"{room['base']}/gifs", headers=auth(room["out"])).status_code == 404
