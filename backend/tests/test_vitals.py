import uuid

from sqlalchemy import select

from app.models import WebVital
from tests.conftest import auth, make_profile

API = "/api/v1"


def test_vitals_accepts_valid_metric_and_rejects_unknown_name(db, client):
    ok = client.post(f"{API}/vitals", json={"name": "LCP", "value": 2310.5, "route": "/lesson/:id"})
    assert ok.status_code == 204
    assert client.post(f"{API}/vitals", json={"name": "FID9", "value": 1, "route": "/"}).status_code == 422
    assert client.post(f"{API}/vitals", json={"name": "LCP", "value": -5, "route": "/"}).status_code == 422
    assert client.post(f"{API}/vitals", json={"name": "LCP", "value": 10_000_000, "route": "/"}).status_code == 422


def test_vitals_summary_is_reviewer_only(db, client):
    for v in (1000, 2000, 3000, 4000):
        client.post(f"{API}/vitals", json={"name": "LCP", "value": v, "route": "/home"})
    student = make_profile(db, "student")
    assert client.get(f"{API}/vitals/summary", headers=auth(student)).status_code == 403
    assert client.get(f"{API}/vitals/summary").status_code == 401
    rev = make_profile(db, "reviewer")
    rows = client.get(f"{API}/vitals/summary", headers=auth(rev)).json()["rows"]
    lcp = next(r for r in rows if r["name"] == "LCP" and r["route"] == "/home")
    assert lcp["n"] == 4 and 3000 <= lcp["p75"] <= 3250


def test_vitals_stores_no_user_id_and_strips_ids_from_routes(db, client):
    p = make_profile(db, "student")
    uid = str(uuid.uuid4())
    client.post(f"{API}/vitals", headers=auth(p), json={"name": "TTFB", "value": 120, "route": f"/lesson/{uid}?token=abc#x"})
    row = db.scalar(select(WebVital).where(WebVital.name == "TTFB"))
    assert row.route == "/lesson/:id"
    assert not hasattr(row, "student_id") and str(p.id) not in str(row.route)
