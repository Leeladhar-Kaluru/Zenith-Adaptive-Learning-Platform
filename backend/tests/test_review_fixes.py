"""Fixes from the independent whole-branch review: each test failed before its fix."""
import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import func, select

from app.cms import gates, importer, review
from app.cms.schema import FigureBlock
from app.core import security
from app.core.config import settings
from app.ingest import commons, fetch as f
from app.ingest.assets import AssetError, approve_asset, retire_asset
from app.models import GateResult, LessonVersion, Source, SourceAsset, WebVital
from tests.conftest import auth, make_profile
from tests.content_fixture import build

API = "/api/v1"
UA = "ZenithBot/1.0 (education; test)"


# ---- 2: robots.txt redirects ------------------------------------------------------------------------------
class Clock:
    t = 100.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


@pytest.fixture()
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(f, "_now", c.now)
    monkeypatch.setattr(f, "_sleep", c.sleep)
    f.reset()
    return c


def test_a_redirected_robots_file_is_followed_on_the_same_host_and_still_obeyed(clock):
    seen = []

    def h(req):
        seen.append(str(req.url))
        if req.url.path == "/robots.txt":
            return httpx.Response(301, headers={"Location": "https://a.example/policy/robots.txt"})
        if req.url.path == "/policy/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
        return httpx.Response(200, content=b"ok")

    with httpx.Client(transport=httpx.MockTransport(h)) as c:
        assert f.fetch("https://a.example/public/x", user_agent=UA, client=c) == b"ok"
        with pytest.raises(f.Disallowed):
            f.fetch("https://a.example/private/x", user_agent=UA, client=c)
    assert not any("/private/x" in u for u in seen)


def test_a_robots_file_that_redirects_to_another_host_or_loops_means_do_not_fetch(clock):
    for loc in ("https://elsewhere.example/robots.txt", "/robots.txt"):
        f.reset()
        with httpx.Client(transport=httpx.MockTransport(lambda r, loc=loc: httpx.Response(302, headers={"Location": loc}) if r.url.path == "/robots.txt" else httpx.Response(200, content=b"x"))) as c:
            with pytest.raises(f.Disallowed):
                f.fetch("https://b.example/x", user_agent=UA, client=c)


# ---- 3 and a minor: retiring an asset is a real kill switch -----------------------------------------------
def _asset(db, **kw):
    s = db.scalar(select(Source)) or Source(name="Test source", homepage="https://t.example")
    db.add(s)
    db.flush()
    now = datetime.now(timezone.utc)
    base = dict(source_id=s.id, external_id=f"x-{uuid.uuid4().hex[:6]}", url="https://t.example/a", kind="dataset", licence_id="CC-BY-4.0", attribution_text="T, CC BY 4.0",
                status="approved", retrieved_at=now, recheck_at=now + timedelta(days=30), data={"fields": ["a"], "rows": [{"a": 1}]})
    base.update(kw)
    a = SourceAsset(**base)
    db.add(a)
    db.commit()
    return a


def test_retiring_an_asset_takes_its_data_off_the_student_pages_and_blocks_reapproval(db, client):
    rev, st = make_profile(db, "reviewer"), make_profile(db, "student")
    a = _asset(db)
    assert client.get(f"{API}/datasets/{a.id}", headers=auth(st)).status_code == 200
    retire_asset(db, a.id, rev.id, "licence changed upstream")
    assert client.get(f"{API}/datasets/{a.id}", headers=auth(st)).status_code == 404
    with pytest.raises(AssetError):
        approve_asset(db, a.id, rev.id)                                   # retired is final until a person re-imports it
    with pytest.raises(AssetError):
        retire_asset(db, uuid.uuid4(), rev.id, "x")


def test_assets_due_for_recheck_are_listed_for_reviewers_only(db, client):
    rev, st = make_profile(db, "reviewer"), make_profile(db, "student")
    _asset(db, recheck_at=datetime.now(timezone.utc) - timedelta(days=2), external_id="old")
    _asset(db, external_id="fresh")
    assert client.get(f"{API}/review/assets-due", headers=auth(st)).status_code == 403
    rows = client.get(f"{API}/review/assets-due", headers=auth(rev)).json()["assets"]
    assert [r["externalId"] for r in rows] == ["old"] and rows[0]["licence"] == "CC-BY-4.0"


# ---- 4 and 5: gates ---------------------------------------------------------------------------------------
def gate(name, blocks, sources=(), assets=None):
    return next(g for g in gates.lesson_gates(title="t", grade=6, objectives=["o"], blocks=blocks, items=[], concept_ids=set(), known_concepts=set(), graph_error=None,
                                               curriculum_verified=True, misconception_codes=set(), sources=list(sources), assets=assets or {}) if g.name == name)


def test_an_image_asset_must_be_stored_on_zenith_before_it_can_be_published():
    fig = [{"kind": "figure", "svg": "", "asset": "a1", "alt": "A labelled cell", "caption": ""}]
    unstored = {"a1": {"status": "approved", "attribution": "x", "kind": "image", "stored": False}}
    stored = {"a1": {"status": "approved", "attribution": "x", "kind": "image", "stored": True}}
    g = gate("Imported assets are credited", fig, ["a1"], unstored)
    assert not g.passed and "stored" in g.detail
    assert gate("Imported assets are credited", fig, ["a1"], stored).passed


@pytest.mark.parametrize("html", ['<img src="https://evil.example/x.png">', '<p>see <a href="https://x.example">this</a></p>', "<iframe src=x></iframe>", "<script>1</script>",
                                  '<svg><image href="https://evil.example/a.png"/></svg>', '<svg><rect style="fill:url(https://x.example/p)"/></svg>'])
def test_markup_that_pulls_in_outside_content_fails_the_gate(html):
    g = gate("No outside references in lesson markup", [{"kind": "text", "html": html}, {"kind": "figure", "svg": html, "alt": "alt text here"}])
    assert not g.passed and "outside" in g.detail.lower()


def test_ordinary_lesson_markup_passes_that_gate():
    ok = [{"kind": "text", "html": "<p>Use <strong>HTTP</strong> carefully. 3 &lt; 5.</p>"}, {"kind": "figure", "svg": '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>', "alt": "A circle"}]
    assert gate("No outside references in lesson markup", ok).passed


# ---- 6: approving an asset after import unsticks the lesson on re-import ----------------------------------
def test_reimport_after_the_asset_is_approved_moves_the_lesson_out_of_draft(db, tmp_path):
    rev = make_profile(db, "reviewer")
    a = _asset(db, kind="dataset", status="pending", data={"fields": ["year", "value"], "rows": [{"year": 1, "value": 2}]})
    tree = importer.load_tree(build(tmp_path / "content"))
    _, lessons = tree.chapters[0]
    first = next(iter(lessons.values()))
    first.sources = [str(a.id)]
    first.blocks.insert(1, __import__("app.cms.schema", fromlist=["WidgetBlock"]).WidgetBlock(kind="widget", widget="data_chart", config={"dataset": str(a.id), "x": "year", "y": "value"}, task="Look at the trend"))
    assert importer.import_tree(db, tree)["draft"] >= 1
    lv = db.scalar(select(LessonVersion).where(LessonVersion.title == first.title))
    assert lv.status == "draft"
    approve_asset(db, a.id, rev.id)
    rep = importer.import_tree(db, tree)
    db.refresh(lv)
    assert lv.status == "in_review" and rep["lesson_versions_created"] == 0 and rep.get("regated", 0) >= 1
    assert db.scalar(select(func.count()).select_from(GateResult).where(GateResult.lesson_version_id == lv.id, GateResult.name == "Imported assets are credited")) == 1   # replaced, not duplicated


def test_a_published_lesson_is_never_regated_by_a_reimport(db, tmp_path):
    rev = make_profile(db, "reviewer")
    tree = importer.load_tree(build(tmp_path / "content"))
    importer.import_tree(db, tree)
    for lv in db.scalars(select(LessonVersion)).all():
        review.approve(db, lv.id, rev.id, manual_confirmed=True)
        review.publish(db, lv.id, rev.id)
    db.commit()
    importer.import_tree(db, tree)
    assert {v for (v,) in db.execute(select(LessonVersion.status))} == {"published"}


# ---- 7: the anonymous vitals endpoint is bounded -----------------------------------------------------------
def test_vitals_routes_are_normalised_capped_and_old_rows_pruned(db, client, monkeypatch):
    from app.services import vitals
    client.post(f"{API}/vitals", json={"name": "LCP", "value": 100, "route": "/a/b/c/d/e?x=1"})
    client.post(f"{API}/vitals", json={"name": "LCP", "value": 100, "route": "/we ird/<script>/x"})
    routes = {r for (r,) in db.execute(select(WebVital.route))}
    assert "/a/b/c" in routes and all(len(r.strip("/").split("/")) <= 3 for r in routes) and not any("<" in r or " " in r for r in routes)
    monkeypatch.setattr(vitals, "DAILY_CAP", 3)
    for _ in range(6):
        client.post(f"{API}/vitals", json={"name": "CLS", "value": 5, "route": "/home"})
    assert db.scalar(select(func.count(WebVital.id)).where(WebVital.name == "CLS")) <= 3
    db.add(WebVital(name="TTFB", value=1, route="/old", at=datetime.now(timezone.utc) - timedelta(days=45)))
    db.commit()
    monkeypatch.setattr(vitals, "DAILY_CAP", 10_000)
    monkeypatch.setattr(vitals, "PRUNE_EVERY", 1)
    client.post(f"{API}/vitals", json={"name": "FCP", "value": 5, "route": "/home"})
    assert db.scalar(select(func.count(WebVital.id)).where(WebVital.route == "/old")) == 0


# ---- 9: a few seconds of clock difference must not log a student out --------------------------------------
KEY = ec.generate_private_key(ec.SECP256R1())


def test_a_token_issued_a_few_seconds_in_the_future_is_accepted_but_a_far_future_one_is_not(monkeypatch):
    import json
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    pub = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(KEY.public_key()))

    async def keys():
        return {"keys": [{**pub, "kid": "k1", "alg": "ES256"}]}

    async def network(tok):
        raise AssertionError("must not fall back to the network")

    monkeypatch.setattr(security, "_fetch_jwks", keys)
    monkeypatch.setattr(security, "_fetch_supabase_user", network)
    security._jwks_cache.update(at=0.0, keys={}, tried=0.0)
    security._token_cache.clear()
    uid = str(uuid.uuid4())

    def tok(iat_offset):
        now = int(time.time())
        return jwt.encode({"sub": uid, "aud": "authenticated", "iss": "https://example.supabase.co/auth/v1", "iat": now + iat_offset, "exp": now + 600}, KEY, algorithm="ES256", headers={"kid": "k1"})

    assert asyncio.run(security.verify_supabase_token(tok(10))) == {"id": uid}
    assert asyncio.run(security.verify_supabase_token(tok(300))) is None


# ---- 1: Wikimedia needs a user agent with real contact details; the owner supplies them -------------------
def test_commons_import_refuses_to_run_without_a_contact_in_the_user_agent(db, monkeypatch):
    monkeypatch.setattr(settings, "BOT_CONTACT", "")
    with pytest.raises(commons.CommonsError, match="BOT_CONTACT"):
        commons.import_file(db, "File:Cell.png", make_profile(db, "reviewer").id)


def test_the_user_agent_carries_the_configured_contact(monkeypatch):
    monkeypatch.setattr(settings, "BOT_CONTACT", "owner@school.example")
    assert "owner@school.example" in commons.user_agent()


def test_the_cli_reports_a_refused_fetch_instead_of_crashing(db, monkeypatch, capsys):
    from app import cli
    monkeypatch.setattr(settings, "BOT_CONTACT", "owner@school.example")

    def refuse(*a, **k):
        raise f.Disallowed("robots.txt does not allow this")
    monkeypatch.setattr(commons, "fetch", refuse)
    make_profile(db, "reviewer")
    assert cli.main(["x", "asset", "commons", "File:Cell.png"]) == 1
    assert "Not imported" in capsys.readouterr().out
