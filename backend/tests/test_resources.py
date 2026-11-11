import io
import zipfile

import pytest

from app.models import ClassMember, Classroom
from app.services import chatfiles
from tests.conftest import auth, make_profile

API = "/api/v1"
PDF = b"%PDF-1.4\n" + b"0" * 64


def office(kind="word", extra=None, content_types=b"<Types/>"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr({"word": "word/document.xml", "xl": "xl/workbook.xml", "ppt": "ppt/presentation.xml"}[kind], "<x/>")
        for name in extra or []:
            z.writestr(name, "x")
    return buf.getvalue()


@pytest.fixture()
def room(db):
    teacher, other = make_profile(db, "teacher"), make_profile(db, "teacher")
    teacher.display_name = "Ms Rao"
    a, b, out = (make_profile(db, "student", nickname=n) for n in ("Asha", "Ben", "Outsider"))
    db.commit()
    cls = Classroom(teacher_id=teacher.id, name="7A", grade=7, subject_id="maths", board_id="cbse", join_code="ZEN-RES1")
    db.add(cls)
    db.commit()
    db.add_all([ClassMember(classroom_id=cls.id, student_id=s.id) for s in (a, b)])
    db.commit()
    return dict(t=teacher, other=other, a=a, b=b, out=out, id=str(cls.id), base=f"{API}/classes/{cls.id}/resources")


@pytest.fixture()
def store(monkeypatch):
    saved = {}
    monkeypatch.setattr(chatfiles, "put", lambda key, data, mime: saved.__setitem__(key, (data, mime)))
    monkeypatch.setattr(chatfiles, "signed_url", lambda key: f"https://files.test/{key}?Authorization=tmp")
    return saved


def upload(client, room, who, data, name="notes.pdf", title="Chapter notes", note=""):
    return client.post(f"{room['base']}/upload", headers=auth(room[who]), params={"name": name, "title": title, "note": note}, content=data)


def listing(client, room, who):
    return client.get(f"{API}/classes/{room['id']}", headers=auth(room[who])).json()["resources"]


def test_a_teacher_shares_a_pdf_and_class_members_see_it_without_the_storage_key(client, room, store):
    r = upload(client, room, "t", PDF, note="Read before Friday")
    assert r.status_code == 200
    rows = listing(client, room, "a")
    assert len(rows) == 1 and rows[0]["title"] == "Chapter notes" and rows[0]["note"] == "Read before Friday" and rows[0]["kind"] == "file"
    assert rows[0]["file"] == {"name": "notes.pdf", "type": "application/pdf", "size": len(PDF)} and "key" not in str(rows) and "classfiles/" not in str(rows)
    key = next(iter(store))
    assert key.startswith(f"classfiles/{room['id']}/") and key.endswith(".pdf")
    assert client.get(f"{API}/classes/{room['id']}", headers=auth(room["out"])).status_code == 404          # not in the class
    assert listing(client, room, "t")[0]["id"] == rows[0]["id"]


def test_only_the_owning_teacher_can_add_or_remove(client, room, store):
    assert upload(client, room, "a", PDF).status_code == 403
    assert upload(client, room, "other", PDF).status_code == 404
    assert upload(client, room, "out", PDF).status_code == 403            # any student gets the same answer for every class id, so nothing about a class can be probed
    link = {"title": "Khan", "url": "https://example.org/x"}
    assert client.post(f"{room['base']}/link", headers=auth(room["a"]), json=link).status_code == 403
    assert client.post(f"{room['base']}/link", headers=auth(room["other"]), json=link).status_code == 404
    rid = upload(client, room, "t", PDF).json()["id"]
    assert client.delete(f"{room['base']}/{rid}", headers=auth(room["a"])).status_code == 403
    assert client.delete(f"{room['base']}/{rid}", headers=auth(room["other"])).status_code == 404
    assert client.delete(f"{room['base']}/{rid}", headers=auth(room["t"])).status_code == 200
    assert listing(client, room, "a") == []


def test_office_documents_are_accepted_and_unsafe_files_are_refused(client, room, store):
    for kind, name, mime in (("word", "worksheet.docx", "wordprocessingml"), ("xl", "marks.xlsx", "spreadsheetml"), ("ppt", "slides.pptx", "presentationml")):
        r = upload(client, room, "t", office(kind), name=name, title=name)
        assert r.status_code == 200, r.text
    assert {x["file"]["type"].split(".")[-1] for x in listing(client, room, "a")} == {"document", "sheet", "presentation"}
    for bad, why in ((b"MZ\x90\x00 program", "exe"), (office("word", extra=["word/vbaProject.bin"]), "macros"), (office("word", content_types=b'<Types><Override ContentType="application/vnd.ms-word.document.macroEnabled.main+xml"/></Types>'), "macro type"),
                     (io.BytesIO().getvalue(), "empty"), (b"PK\x03\x04 not really a zip", "fake zip")):
        assert upload(client, room, "t", bad, name="x.docx").status_code == 422, why
    plain = io.BytesIO()
    with zipfile.ZipFile(plain, "w") as z:
        z.writestr("hello.txt", "hi")
    assert upload(client, room, "t", plain.getvalue(), name="a.zip").status_code == 422                       # a zip that is not an office file
    assert upload(client, room, "t", PDF + b"0" * (chatfiles.MAX_BYTES + 1)).status_code == 413
    assert upload(client, room, "t", PDF, title="   ").status_code == 422


def test_links_must_be_plain_web_addresses(client, room):
    ok = client.post(f"{room['base']}/link", headers=auth(room["t"]), json={"title": "<b>Fractions</b> video", "url": "https://www.example.org/watch?v=1", "note": "<script>x</script>Watch it"})
    assert ok.status_code == 200
    row = listing(client, room, "b")[0]
    assert row["kind"] == "link" and row["url"] == "https://www.example.org/watch?v=1" and row["title"] == "Fractions video" and row["note"] == "Watch it" and row["file"] is None
    for bad in ("javascript:alert(1)", "data:text/html,hi", "ftp://example.org/a", "//example.org/x", "https://user:pw@example.org/", "https://", "https://exa mple.org", "example.org", "https://" + "a" * 600 + ".org"):
        assert client.post(f"{room['base']}/link", headers=auth(room["t"]), json={"title": "x", "url": bad}).status_code == 422, bad
    assert client.post(f"{room['base']}/link", headers=auth(room["t"]), json={"title": " ", "url": "https://example.org"}).status_code == 422
    assert client.post(f"{room['base']}/link", headers=auth(room["t"]), json={"title": "t" * 121, "url": "https://example.org"}).status_code == 422


def test_download_links_are_short_lived_and_for_members_only(client, room, store, db):
    rid = upload(client, room, "t", PDF).json()["id"]
    got = client.get(f"{room['base']}/{rid}/file", headers=auth(room["a"])).json()
    assert got["url"].startswith("https://files.test/classfiles/") and got["name"] == "notes.pdf" and got["expiresIn"] == chatfiles.LINK_SECONDS
    assert client.get(f"{room['base']}/{rid}/file", headers=auth(room["t"])).status_code == 200
    assert client.get(f"{room['base']}/{rid}/file", headers=auth(room["out"])).status_code == 404
    link = client.post(f"{room['base']}/link", headers=auth(room["t"]), json={"title": "Site", "url": "https://example.org"}).json()["id"]
    assert client.get(f"{room['base']}/{link}/file", headers=auth(room["a"])).status_code == 404            # a link has no file
    client.delete(f"{API}/classes/{room['id']}/membership", headers=auth(room["a"]))
    assert client.get(f"{room['base']}/{rid}/file", headers=auth(room["a"])).status_code == 404            # leaving ends access to files


def test_resources_are_listed_newest_first_and_the_class_cards_count_them(client, room, store):
    upload(client, room, "t", PDF, title="First")
    upload(client, room, "t", PDF, title="Second")
    assert [r["title"] for r in listing(client, room, "a")] == ["Second", "First"]
    assert client.get(f"{API}/classes", headers=auth(room["a"])).json()[0]["resources"] == 2
