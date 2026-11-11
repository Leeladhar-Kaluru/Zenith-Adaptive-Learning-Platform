import asyncio
import json
from types import SimpleNamespace as NS

import pytest
from sqlalchemy import select

from app.cms import evaluator, infographic
from app.core.config import settings
from app.ingest import textsource
from app.models import Concept, IngestJob, LessonDraft, LessonVersion, Notification, SourceAsset
from app.services import coverage, pipeline
from tests.conftest import auth, make_profile
from tests.test_api import API, world  # noqa: F401  (the published sample content)
from tests.test_autodraft import good

INDEX = "https://open.example.org/facts/"
PAGE = "https://open.example.org/facts/volcano-basics.html"
BODY = ("A volcano is an opening in the Earth's crust where hot melted rock called magma comes out as lava. Volcanoes form where plates of the crust meet and "
        "move apart or together. When pressure builds up under the ground the magma rises and erupts through a vent. Over many eruptions the lava cools and "
        "builds a cone shaped mountain. Some volcanoes are active and erupt often while others are dormant and have been quiet for a very long time.")


def site(url, *, user_agent):
    if url == INDEX:
        return b'<html><body><a href="/facts/volcano-basics.html">How a volcano works</a><a href="/facts/tides.html">What are tides?</a><a href="/about">About us</a></body></html>'
    if url == PAGE:
        return f"<html><body><main><h1>How a volcano works</h1><h2>Magma and lava</h2><p>{BODY}</p></main></body></html>".encode()
    raise OSError("not found")


@pytest.fixture(autouse=True)
def open_source(monkeypatch):
    src = textsource.OpenSource(name="OpenTest", hosts=("open.example.org",), path_prefix="/facts/", licence="US-GOV-PD", homepage="https://open.example.org/", proof="publisher",
                                terms="https://open.example.org/terms", attribution="Adapted from OpenTest, {title} ({url}). Public domain.", index_urls=(INDEX,))
    monkeypatch.setattr(textsource, "SOURCES", {"open-test": src})


@pytest.fixture()
def people(db, world):
    reviewer = world["reviewer"]
    s7, s7b, s8 = (make_profile(db, "student", grade=g) for g in (7, 7, 8))
    db.add(Concept(id="volcanoes", title="How volcanoes work", description="d", grade=7, subject_id="maths", keywords=["volcano", "magma", "lava"], enrichment=False))
    db.commit()
    return dict(reviewer=reviewer, s7=s7, s7b=s7b, s8=s8)


def test_publishing_a_lesson_tells_each_student_of_that_class_once(client, db, world):
    other_grade = make_profile(db, "student", grade=10)
    db.commit()
    lv = db.scalars(select(LessonVersion).where(LessonVersion.status == "published")).first()
    from app.cms import review
    lv.status = "approved"
    db.flush()
    review.publish(db, lv.id, world["reviewer"].id)
    db.commit()
    mine = client.get(f"{API}/notifications", headers=world["h"]).json()
    assert mine["unread"] == 1 and mine["items"][0]["kind"] == "new_lesson" and mine["items"][0]["link"].startswith("/lesson/")
    assert db.scalars(select(Notification).where(Notification.user_id == other_grade.id)).all() == []                  # a different class hears nothing
    assert client.post(f"{API}/notifications/read", headers=world["h"], json={}).json()["marked"] == 1
    assert client.get(f"{API}/notifications", headers=world["h"]).json()["unread"] == 0


def test_coverage_counts_real_rows_and_a_request_counts_each_student_once(client, db, people):
    rows = client.get(f"{API}/coverage", headers=auth(people["s7"])).json()["rows"]
    maths = next(r for r in rows if r["subject"] == "maths")
    assert maths["topics"] > maths["topicsCovered"] and "How volcanoes work" in maths["missingTopics"] and maths["youRequested"] is False
    a = client.post(f"{API}/coverage/request", headers=auth(people["s7"]), json={"subject": "maths"}).json()
    again = client.post(f"{API}/coverage/request", headers=auth(people["s7"]), json={"subject": "maths"}).json()
    b = client.post(f"{API}/coverage/request", headers=auth(people["s7b"]), json={"subject": "maths"}).json()
    assert a["demand"] == 1 and again["demand"] == 1 and b["demand"] == 2 and a["id"] == b["id"]
    assert client.post(f"{API}/coverage/request", headers=auth(people["s7"]), json={"subject": "nonsense"}).status_code == 422
    assert client.post(f"{API}/coverage/request", headers=auth(people["reviewer"]), json={"subject": "maths"}).status_code == 403
    assert next(r for r in client.get(f"{API}/coverage", headers=auth(people["s7"])).json()["rows"] if r["subject"] == "maths")["youRequested"] is True
    assert next((r for r in client.get(f"{API}/coverage", headers=auth(people["s8"])).json()["rows"] if r["subject"] == "maths"), {}).get("youRequested", False) is False


def test_a_request_finds_a_vetted_page_for_a_missing_topic_and_stores_it_pending_never_published(client, db, people):
    client.post(f"{API}/coverage/request", headers=auth(people["s7"]), json={"subject": "maths", "topic": "volcano"})
    out = pipeline.run_requests(db, fetcher=site)
    assert out["requests"] == 1 and out["pages"] == 1
    a = db.scalar(select(SourceAsset).where(SourceAsset.external_id == PAGE))
    assert a.status == "pending" and a.kind == "text" and "OpenTest" in a.attribution_text and a.licence_id == "US-GOV-PD"
    job = db.scalar(select(IngestJob).where(IngestJob.kind == "request"))
    assert job.status == "done" and job.result["imported"][0]["concept"] == "volcanoes"
    assert db.scalars(select(Notification).where(Notification.user_id == people["reviewer"].id, Notification.kind == "pipeline")).all()      # reviewers are told
    again = pipeline.run_requests(db, fetcher=site)
    assert again["requests"] == 0                                                                                            # nothing queued is left, and the page is not imported twice


def test_a_request_with_no_matching_page_is_blocked_with_a_reason_not_faked(client, db, people):
    db.get(Concept, "volcanoes").keywords = ["glacier"]
    db.commit()
    client.post(f"{API}/coverage/request", headers=auth(people["s7"]), json={"subject": "maths"})
    out = pipeline.run_requests(db, fetcher=site)
    job = db.scalar(select(IngestJob).where(IngestJob.kind == "request"))
    assert out["pages"] == 0 and job.status == "blocked" and "No open-licence source page" in job.error
    assert db.scalars(select(SourceAsset)).all() == []


def test_drafts_need_the_ai_helper_and_an_approved_page_and_always_wait_for_a_person(client, db, people):
    client.post(f"{API}/coverage/request", headers=auth(people["s7"]), json={"subject": "maths", "topic": "volcano"})
    pipeline.run_requests(db, fetcher=site)
    a = db.scalar(select(SourceAsset).where(SourceAsset.external_id == PAGE))

    async def gen(**_):
        return json.dumps({**good(), "infographic": {"type": "flow", "title": "How a volcano erupts", "steps": ["Magma builds up", "Pressure rises", "Lava erupts"]}})

    assert asyncio.run(pipeline.run_drafts(db, None))["skipped"]                                    # AI off: reported, nothing made
    assert asyncio.run(pipeline.run_drafts(db, gen))["drafted"] == 0                                # page not approved yet
    a.status = "approved"
    db.commit()
    out = asyncio.run(pipeline.run_drafts(db, gen))
    d = db.scalar(select(LessonDraft))
    assert out["drafted"] + out["rejected"] == 1 and d.status == "ready" and d.lesson["origin"] == "ai_assisted" and d.scorecard["checks"]
    assert not any("TODO" in b.get("svg", "") for b in d.lesson["blocks"] if b["kind"] == "figure")                 # the infographic filled the diagram slot
    assert db.scalars(select(LessonVersion).where(LessonVersion.title == d.title)).all() == []                      # never entered the student-facing tables
    assert asyncio.run(pipeline.run_drafts(db, gen))["drafted"] == 0 and len(db.scalars(select(LessonDraft)).all()) == 1


def test_the_evaluator_rejects_copying_and_malformed_questions_and_explains_each_mark():
    lesson = {"origin": "ai_assisted", "sources": ["x"], "objectives": ["a", "b", "c"], "misconceptions": [{}, {}],
              "blocks": [{"kind": "text", "html": f"<p>{BODY}</p>"}, {"kind": "example", "prompt": "p", "steps": ["s"]}, {"kind": "example", "prompt": "p", "steps": ["s"]},
                         {"kind": "summary", "points": ["a", "b", "c"]}],
              "items": [{"key": f"q{i}", "stem": f"Stem {i}", "difficulty": ["intro", "standard", "challenge"][i % 3], "correct": "AB"[i % 2],
                         "options": [{"key": k, "text": f"opt {k} {i}"} for k in "ABCD"]} for i in range(8)]}
    card = evaluator.evaluate(lesson, BODY, 7)
    assert card["verdict"] == "rejected" and "Rewritten, not copied" in card["rejectedBecause"]
    lesson["blocks"][0]["html"] = "<p>Hot melted rock rises under a mountain. It breaks out through a crack and flows down the sides. Later it cools and turns hard.</p>"
    lesson["items"][0]["options"][1]["text"] = lesson["items"][0]["options"][0]["text"]
    card = evaluator.evaluate(lesson, BODY, 7)
    assert card["verdict"] == "rejected" and any(not c["passed"] and "four different options" in c["name"] for c in card["checks"])
    lesson["items"][0]["options"][1]["text"] = "something else"
    ok = evaluator.evaluate(lesson, BODY, 7)
    assert ok["verdict"] == "review" and 0 < ok["score"] <= 1 and all(c["detail"] for c in ok["checks"])


def test_infographics_are_escaped_plain_svg_with_an_alt_text_and_bad_specs_are_refused():
    svg, alt = infographic.build({"type": "flow", "title": "Water <script>x</script> cycle", "steps": ["Sun heats water", "Vapour rises & cools", "Rain falls"]})
    assert svg.startswith("<svg") and "<script" not in svg and "&amp;" in svg and "http" not in svg.replace("http://www.w3.org/2000/svg", "") and "Step 2: Vapour" in alt
    svg2, alt2 = infographic.build({"type": "compare", "title": "Sound and light", "left_name": "Sound", "left": ["Needs air"], "right_name": "Light", "right": ["Travels in space"]})
    assert "Sound" in alt2 and svg2.count("<rect") >= 4
    for bad in (None, {"type": "flow", "steps": ["only one"]}, {"type": "compare", "left_name": "", "left": ["a"], "right_name": "b", "right": ["c"]}, {"type": "pie"}):
        with pytest.raises(ValueError):
            infographic.build(bad)


def test_the_scheduled_run_needs_the_secret_and_the_pipeline_screens_are_for_reviewers_only(client, db, people, monkeypatch):
    assert client.get(f"{API}/ingest/run").status_code == 401
    monkeypatch.setattr(settings, "CRON_SECRET", "s3cret-for-tests")
    assert client.get(f"{API}/ingest/run", headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.get(f"{API}/ingest/run", headers={"Authorization": "Bearer s3cret-for-tests"})
    assert ok.status_code == 200 and "requests" in ok.json()
    assert client.get(f"{API}/pipeline/overview", headers=auth(people["s7"])).status_code == 403
    ov = client.get(f"{API}/pipeline/overview", headers=auth(people["reviewer"])).json()
    assert ov["cronConfigured"] is True and set(ov) >= {"jobs", "pages", "drafts", "queued", "aiEnabled"}


def test_the_api_starts_without_sympy_and_yaml_because_the_serverless_runtime_does_not_install_them():
    import subprocess
    import sys
    code = "import sys\nfor m in ('sympy', 'yaml'):\n    sys.modules[m] = None\nimport app.main\n"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    assert r.returncode == 0, r.stderr[-400:]
