from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.cms import gates, importer, review
from app.cms.schema import FigureBlock
from app.models import ContentProvenance, LessonVersion, Source, SourceAsset
from tests.conftest import auth, make_profile
from tests.content_fixture import build

API = "/api/v1"


def run_gate(blocks, sources, assets):
    return next(g for g in gates.lesson_gates(
        title="t", grade=6, objectives=["o"], blocks=blocks, items=[], concept_ids=set(), known_concepts=set(), graph_error=None, curriculum_verified=True,
        misconception_codes=set(), sources=sources, assets=assets) if g.name == "Imported assets are credited")


FIG = {"kind": "figure", "svg": "", "asset": "a1", "alt": "A labelled cell", "caption": ""}
OK = {"a1": {"status": "approved", "attribution": "Cell by Ann, CC BY 4.0"}}


def test_gate_passes_when_there_are_no_imported_assets():
    g = run_gate([{"kind": "text", "html": "x"}], [], {})
    assert g.passed


def test_figure_using_an_unlisted_asset_fails():
    assert not run_gate([FIG], [], OK).passed


def test_listed_asset_must_exist_be_approved_and_credited():
    assert run_gate([FIG], ["a1"], OK).passed
    assert not run_gate([FIG], ["a1"], {}).passed
    assert not run_gate([FIG], ["a1"], {"a1": {"status": "pending", "attribution": "x"}}).passed
    assert not run_gate([FIG], ["a1"], {"a1": {"status": "approved", "attribution": "  "}}).passed


def test_figure_needs_exactly_one_of_svg_or_asset():
    with pytest.raises(ValueError):
        FigureBlock(kind="figure", svg="", alt="alt text here", caption="")
    with pytest.raises(ValueError):
        FigureBlock(kind="figure", svg="<svg/>", asset="a1", alt="alt text here", caption="")
    FigureBlock(kind="figure", asset="a1", alt="alt text here", caption="")


@pytest.fixture()
def world(db, tmp_path):
    reviewer = make_profile(db, "reviewer")
    src = Source(name="Wikimedia Commons", homepage="https://commons.wikimedia.org", licence_terms_url="u")
    db.add(src)
    db.flush()
    now = datetime.now(timezone.utc)
    asset = SourceAsset(source_id=src.id, external_id="File:Cell.png", url="https://upload.wikimedia.org/x/Cell.png", kind="image", licence_id="CC-BY-4.0",
                        attribution_text="Cell.png by Ann Lee, CC BY 4.0, via Wikimedia Commons", author="Ann Lee", status="approved", retrieved_at=now,
                        recheck_at=now + timedelta(days=180), reviewer_id=reviewer.id)
    db.add(asset)
    db.commit()
    tree = importer.load_tree(build(tmp_path / "content"))
    return reviewer, asset, tree


def test_credited_lesson_imports_publishes_and_shows_its_credit(db, client, world):
    reviewer, asset, tree = world
    _, lessons = tree.chapters[0]
    first = next(iter(lessons.values()))
    first.sources = [str(asset.id)]
    first.blocks.insert(1, FigureBlock(kind="figure", asset=str(asset.id), alt="A labelled plant cell", caption="A cell."))
    rep = importer.import_tree(db, tree)
    assert rep["draft"] == 0
    for lv in db.scalars(select(LessonVersion)).all():
        review.approve(db, lv.id, reviewer.id, manual_confirmed=True)
        review.publish(db, lv.id, reviewer.id)
    db.commit()
    assert db.scalar(select(ContentProvenance.asset_id)) == asset.id
    student = make_profile(db, "student", grade=6)
    lv = db.scalar(select(LessonVersion).where(LessonVersion.title == first.title))
    body = client.get(f"{API}/library/lessons/{lv.lesson_id}", headers=auth(student)).json()
    assert body["credits"] == [{"text": asset.attribution_text, "url": asset.url, "licence": "CC-BY-4.0"}]
    fig = next(b for b in body["blocks"] if b["kind"] == "figure" and b.get("asset"))
    assert fig["imageUrl"] == asset.url


def test_uncredited_use_is_kept_out_of_review(db, world):
    reviewer, asset, tree = world
    _, lessons = tree.chapters[0]
    first = next(iter(lessons.values()))
    first.blocks.insert(1, FigureBlock(kind="figure", asset=str(asset.id), alt="A labelled plant cell", caption="A cell."))   # not listed in sources
    rep = importer.import_tree(db, tree)
    assert rep["draft"] >= 1
    lv = db.scalar(select(LessonVersion).where(LessonVersion.title == first.title))
    assert lv.status == "draft"


def test_lessons_without_sources_keep_their_hash(db, tmp_path):
    t1 = importer.load_tree(build(tmp_path / "a"))
    importer.import_tree(db, t1)
    rep = importer.import_tree(db, importer.load_tree(build(tmp_path / "b")))
    assert rep["lesson_versions_created"] == 0 and rep["lesson_versions_unchanged"] > 0
