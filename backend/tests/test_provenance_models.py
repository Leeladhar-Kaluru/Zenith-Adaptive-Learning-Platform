import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ContentProvenance, Source, SourceAsset
from tests.conftest import make_profile


def src(db, name="Wikimedia Commons"):
    s = Source(name=name, homepage="https://commons.wikimedia.org", licence_terms_url="https://commons.wikimedia.org/wiki/Commons:Licensing", robots_ok=True)
    db.add(s)
    db.commit()
    return s


def asset(source, **kw):
    base = dict(source_id=source.id, external_id=f"File:{uuid.uuid4().hex[:6]}.jpg", url="https://example.org/a.jpg", kind="image", licence_id="CC-BY-4.0",
                attribution_text="Photo by A. Person, CC BY 4.0", author="A. Person", sha256="a" * 64, bytes=1000, status="pending",
                retrieved_at=datetime.now(timezone.utc), recheck_at=datetime.now(timezone.utc) + timedelta(days=180))
    base.update(kw)
    return SourceAsset(**base)


def test_asset_without_licence_is_rejected(db):
    s = src(db)
    db.add(asset(s, licence_id=None))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(asset(s, licence_id=""))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_asset_without_attribution_cannot_be_approved(db):
    s = src(db)
    db.add(asset(s, status="approved", attribution_text=""))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(asset(s, status="pending", attribution_text=""))      # a pending asset may still be incomplete
    db.commit()


def test_duplicate_external_id_in_one_source_is_rejected(db):
    s = src(db)
    db.add(asset(s, external_id="File:Same.jpg"))
    db.commit()
    db.add(asset(s, external_id="File:Same.jpg"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_source_with_assets_cannot_be_deleted(db):
    s = src(db)
    db.add(asset(s))
    db.commit()
    db.delete(s)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_provenance_links_a_lesson_version_to_an_asset(db):
    from app.models import Chapter, CurriculumVersion, Lesson, LessonVersion, Subject
    make_profile(db, "student")
    cv = CurriculumVersion(board_id="cbse", label="t", effective_year=2025, verified=True)
    db.add(cv)
    db.flush()
    ch = Chapter(slug="p-ch", version_id=cv.id, grade=7, subject_id="maths", title="t", summary="s", status="in_production")
    db.add(ch)
    db.flush()
    les = Lesson(chapter_id=ch.id, slug="p", position=1)
    db.add(les)
    db.flush()
    lv = LessonVersion(lesson_id=les.id, version=1, language="en", title="T", minutes=5, objectives=["o"], blocks=[], status="draft", origin="human", content_hash="h")
    s = src(db)
    a = asset(s)
    db.add_all([lv, a])
    db.flush()
    db.add(ContentProvenance(lesson_version_id=lv.id, asset_id=a.id))
    db.commit()
    db.add(ContentProvenance(lesson_version_id=lv.id, asset_id=a.id))        # same link twice
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_assets_past_their_recheck_date_are_reported(db):
    from app.ingest.recheck import due_for_recheck
    s = src(db)
    old = datetime.now(timezone.utc) - timedelta(days=1)
    db.add_all([asset(s, status="approved", recheck_at=old), asset(s, status="approved"), asset(s, status="pending", recheck_at=old), asset(s, status="retired", recheck_at=old)])
    db.commit()
    due = due_for_recheck(db)
    assert len(due) == 1 and due[0].status == "approved"
