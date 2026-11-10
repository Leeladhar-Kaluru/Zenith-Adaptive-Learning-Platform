import yaml
import pytest
from sqlalchemy import select

from app.cms import draft, importer, review
from app.cms.schema import LessonFile
from app.models import LessonVersion
from tests.conftest import make_profile
from tests.content_fixture import build


def test_skeleton_is_schema_valid_and_labelled_ai_assisted():
    d = draft.new_lesson_skeleton("c", "my-lesson", "My lesson", ["number-line"])
    lf = LessonFile(**d)
    assert lf.origin == "ai_assisted" and lf.slug == "my-lesson" and lf.concepts == ["number-line"]


def test_skeleton_lists_every_unfinished_part():
    d = draft.new_lesson_skeleton("c", "my-lesson", "My lesson", ["number-line"])
    found = draft.find_todos(d)
    assert len(found) >= 6 and any("objectives" in f for f in found) and any("blocks" in f for f in found) and any("items" in f for f in found)


def test_validation_fails_until_the_todos_are_replaced(tmp_path):
    root = build(tmp_path / "content")
    path = draft.write_skeleton(root, "7-maths-integers", "new-one", "New one", ["number-line"])
    tree = importer.load_tree(root)
    errs = importer.validate_tree(tree)
    assert any("TODO" in e for e in errs)
    text = path.read_text(encoding="utf-8").replace("TODO", "Done")
    path.write_text(text, encoding="utf-8")
    assert not any("TODO" in e for e in importer.validate_tree(importer.load_tree(root)))


def test_a_skeleton_can_never_reach_review_or_publication(db, tmp_path):
    root = build(tmp_path / "content")
    draft.write_skeleton(root, "7-maths-integers", "new-one", "New one", ["number-line"])
    tree = importer.load_tree(root)
    with pytest.raises(importer.ContentError, match="TODO"):
        importer.import_tree(db, tree)           # an unfinished lesson is not even imported as a draft


def test_write_skeleton_adds_the_lesson_to_the_chapter_and_refuses_overwrite(tmp_path):
    root = build(tmp_path / "content")
    chapter_file = next((root / "chapters").glob("*/chapter.yaml"))
    chapter = yaml.safe_load(chapter_file.read_text(encoding="utf-8"))
    slug = chapter["slug"]
    p = draft.write_skeleton(root, slug, "extra", "Extra", ["number-line"])
    assert p.exists() and "extra" in yaml.safe_load(chapter_file.read_text(encoding="utf-8"))["lessons"]
    with pytest.raises(draft.DraftError):
        draft.write_skeleton(root, slug, "extra", "Extra", ["number-line"])
    with pytest.raises(draft.DraftError):
        draft.write_skeleton(root, "no-such-chapter", "x", "X", ["number-line"])
