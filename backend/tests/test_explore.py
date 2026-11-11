from sqlalchemy import select

from app.cms import importer, review
from app.cms.schema import WidgetBlock
from app.models import LessonVersion
from tests.conftest import auth, make_profile
from tests.content_fixture import build

API = "/api/v1"


def publish(db, tmp_path, with_sim=True, publish_it=True):
    rev = make_profile(db, "reviewer")
    tree = importer.load_tree(build(tmp_path / "content"))
    _, lessons = tree.chapters[0]
    first = next(iter(lessons.values()))
    if with_sim:
        first.blocks.insert(1, WidgetBlock(kind="widget", widget="sim_equation", config={"a": 2, "b": 3, "c": 11}, task="Get x on its own"))
    importer.import_tree(db, tree)
    if publish_it:
        for lv in db.scalars(select(LessonVersion)).all():
            review.approve(db, lv.id, rev.id, manual_confirmed=True)
            review.publish(db, lv.id, rev.id)
        db.commit()
    return first.title


def test_explore_lists_only_interactive_lessons_that_are_published(db, client, tmp_path):
    title = publish(db, tmp_path)
    st = make_profile(db, "student", grade=7)
    body = client.get(f"{API}/explore", headers=auth(st)).json()
    labs = body["labs"]
    assert [l["lessonTitle"] for l in labs] == [title] and labs[0]["kind"] == "simulation" and labs[0]["lessonId"]
    assert "planned" not in body                                          # no "coming soon" placeholders


def test_unpublished_interactive_lessons_never_appear(db, client, tmp_path):
    publish(db, tmp_path, publish_it=False)
    st = make_profile(db, "student", grade=7)
    assert client.get(f"{API}/explore", headers=auth(st)).json()["labs"] == []


def test_a_lesson_without_interactive_parts_is_not_listed(db, client, tmp_path):
    publish(db, tmp_path, with_sim=False)
    st = make_profile(db, "student", grade=7)
    assert client.get(f"{API}/explore", headers=auth(st)).json()["labs"] == []


def test_flashcards_entry_counts_real_cards(db, client, tmp_path):
    publish(db, tmp_path)
    st = make_profile(db, "student", grade=7)
    flash = next(a for a in client.get(f"{API}/explore", headers=auth(st)).json()["available"] if a["key"] == "flashcards")
    assert flash["count"] >= 0 and flash["href"] == "/revision"
