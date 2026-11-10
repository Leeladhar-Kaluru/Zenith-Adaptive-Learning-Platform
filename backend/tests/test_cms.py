import uuid

import pytest
import yaml
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.cms import importer, review
from app.cms.importer import ContentError
from app.models import Chapter, GateResult, Item, Lesson, LessonVersion
from tests.conftest import make_profile
from tests.content_fixture import build


def load(tmp_path, **kw):
    return importer.load_tree(build(tmp_path / "content", **kw))


def versions(db):
    return {lv.title: lv for lv in db.scalars(select(LessonVersion))}


def test_import_creates_reviewable_versions_with_gates(db, tmp_path):
    rep = importer.import_tree(db, load(tmp_path))
    assert rep["lesson_versions_created"] == 2 and rep["in_review"] == 2 and rep["draft"] == 0
    lv = versions(db)["Moving on the line"]
    assert lv.status == "in_review" and lv.reviewer_id is None
    gates = {g.name: g for g in db.scalars(select(GateResult).where(GateResult.lesson_version_id == lv.id))}
    assert gates["Answers verified with SymPy"].passed
    assert gates["Prerequisite graph is acyclic"].passed
    assert gates["Curriculum mapping confirmed"].manual and not gates["Curriculum mapping confirmed"].passed
    assert db.scalar(select(Chapter.status).where(Chapter.slug == "7-maths-integers")) == "in_production"


def test_import_is_idempotent(db, tmp_path):
    tree = load(tmp_path)
    importer.import_tree(db, tree)
    again = importer.import_tree(db, load(tmp_path))
    assert again["lesson_versions_created"] == 0 and again["lesson_versions_unchanged"] == 2
    assert db.query(LessonVersion).count() == 2


def test_wrong_answer_key_fails_sympy_gate_and_blocks_review(db, tmp_path):
    rep = importer.import_tree(db, load(tmp_path, bad_answer=True))
    lv = versions(db)["Moving on the line"]
    assert lv.status == "draft" and rep["draft"] == 1
    g = db.get(GateResult, (lv.id, "Answers verified with SymPy"))
    assert not g.passed and "q-line-1" in g.detail
    with pytest.raises(review.ReviewError):
        review.approve(db, lv.id, make_profile(db, "teacher").id, manual_confirmed=True)


def test_cycle_in_prerequisites_is_rejected(db, tmp_path):
    root = build(tmp_path / "content")
    p = root / "concepts" / "maths.yaml"
    data = yaml.safe_load(p.read_text())
    data["concepts"][0]["prerequisites"] = [{"id": "adding-integers"}]
    p.write_text(yaml.safe_dump(data))
    with pytest.raises(ContentError, match="cycle"):
        importer.import_tree(db, importer.load_tree(root))


def test_unknown_concept_reference_is_rejected(db, tmp_path):
    root = build(tmp_path / "content")
    f = root / "chapters" / "7-maths-integers" / "lessons" / "line.yaml"
    d = yaml.safe_load(f.read_text())
    d["items"][1]["concepts"] = [{"id": "no-such-concept"}]
    f.write_text(yaml.safe_dump(d))
    with pytest.raises(ContentError, match="no-such-concept"):
        importer.import_tree(db, importer.load_tree(root))


def test_approval_needs_manual_confirmation_then_a_named_reviewer(db, tmp_path):
    importer.import_tree(db, load(tmp_path))
    lv = versions(db)["Moving on the line"]
    teacher = make_profile(db, "teacher")
    with pytest.raises(review.ReviewError, match="Confirm"):
        review.approve(db, lv.id, teacher.id)
    review.approve(db, lv.id, teacher.id, manual_confirmed=True)
    db.commit()
    lv = db.get(LessonVersion, lv.id)
    assert lv.status == "approved" and lv.reviewer_id == teacher.id and lv.reviewed_at is not None
    assert {i.status for i in db.scalars(select(Item).where(Item.key.like("q-line-%")))} == {"approved"}


def test_chapter_is_published_only_when_every_lesson_is(db, tmp_path):
    importer.import_tree(db, load(tmp_path))
    teacher = make_profile(db, "teacher")
    vs = versions(db)
    review.approve(db, vs["Moving on the line"].id, teacher.id, manual_confirmed=True)
    review.publish(db, vs["Moving on the line"].id, teacher.id)
    db.commit()
    assert db.scalar(select(Chapter.status)) == "in_production"
    review.approve(db, vs["Adding integers"].id, teacher.id, manual_confirmed=True)
    review.publish(db, vs["Adding integers"].id, teacher.id)
    db.commit()
    assert db.scalar(select(Chapter.status)) == "published"
    review.archive(db, vs["Adding integers"].id, teacher.id)
    db.commit()
    assert db.scalar(select(Chapter.status)) == "in_production"


def test_cannot_publish_unapproved_and_request_changes_flow(db, tmp_path):
    importer.import_tree(db, load(tmp_path))
    lv = versions(db)["Moving on the line"]
    teacher = make_profile(db, "teacher")
    with pytest.raises(review.ReviewError):
        review.publish(db, lv.id, teacher.id)
    with pytest.raises(review.ReviewError):
        review.request_changes(db, lv.id, teacher.id, " ")
    review.request_changes(db, lv.id, teacher.id, "Add a second worked example.")
    assert db.get(LessonVersion, lv.id).status == "changes_requested"


def test_edited_lesson_becomes_a_new_version_and_the_live_one_stays(db, tmp_path):
    importer.import_tree(db, load(tmp_path))
    teacher = make_profile(db, "teacher")
    v1 = versions(db)["Moving on the line"]
    review.approve(db, v1.id, teacher.id, manual_confirmed=True)
    review.publish(db, v1.id, teacher.id)
    db.commit()
    root = tmp_path / "content"
    f = root / "chapters" / "7-maths-integers" / "lessons" / "line.yaml"
    d = yaml.safe_load(f.read_text())
    d["blocks"][0]["html"] = "<p>Numbers can be below zero. We draw them on a line.</p>"
    f.write_text(yaml.safe_dump(d))
    importer.import_tree(db, importer.load_tree(root))
    lvs = list(db.scalars(select(LessonVersion).where(LessonVersion.title == "Moving on the line").order_by(LessonVersion.version)))
    assert [(x.version, x.status) for x in lvs] == [(1, "published"), (2, "in_review")]
    # unchanged items are reused, not duplicated
    assert db.query(Item).filter(Item.key == "q-line-1").count() == 1


def test_changed_item_gets_a_new_version_without_touching_the_published_one(db, tmp_path):
    importer.import_tree(db, load(tmp_path))
    teacher = make_profile(db, "teacher")
    v1 = versions(db)["Moving on the line"]
    review.approve(db, v1.id, teacher.id, manual_confirmed=True)
    review.publish(db, v1.id, teacher.id)
    db.commit()
    f = tmp_path / "content" / "chapters" / "7-maths-integers" / "lessons" / "line.yaml"
    d = yaml.safe_load(f.read_text())
    d["items"][0]["stem"] = "Compute 2 - 5."
    f.write_text(yaml.safe_dump(d))
    importer.import_tree(db, importer.load_tree(tmp_path / "content"))
    rows = list(db.scalars(select(Item).where(Item.key == "q-line-1").order_by(Item.version)))
    assert [(r.version, r.status) for r in rows] == [(1, "published"), (2, "draft")]
    assert rows[0].stem == "What is 2 - 5?"


def test_database_refuses_published_content_without_a_reviewer(db, tmp_path):
    importer.import_tree(db, load(tmp_path))
    lv = versions(db)["Moving on the line"]
    with pytest.raises(IntegrityError):
        db.query(LessonVersion).filter(LessonVersion.id == lv.id).update({"status": "published"})
        db.commit()
    db.rollback()


def test_only_one_published_version_per_lesson(db, tmp_path):
    importer.import_tree(db, load(tmp_path))
    lv = versions(db)["Moving on the line"]
    teacher = make_profile(db, "teacher")
    review.approve(db, lv.id, teacher.id, manual_confirmed=True)
    review.publish(db, lv.id, teacher.id)
    db.commit()
    dup = LessonVersion(lesson_id=lv.lesson_id, version=9, title="x", content_hash="z", status="published", reviewer_id=teacher.id,
                        reviewed_at=lv.reviewed_at)
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
