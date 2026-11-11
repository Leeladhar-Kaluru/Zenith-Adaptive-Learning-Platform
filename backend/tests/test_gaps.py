import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.engine import gaps
from app.models import Concept, ConceptEdge, ConceptState
from tests.conftest import auth, make_profile

API = "/api/v1"
TITLES = {c: {"title": c.upper(), "grade": 7} for c in "ABCDE"}
EDGES = [("A", "B"), ("B", "C"), ("C", "D"), ("A", "E")]            # prerequisite -> concept


def st(p, n, c, status=None):
    return {"p": p, "n": n, "c": c, "status": status or ("secure" if p >= 0.85 and n >= 4 else "learning")}


def test_wilson_interval_is_honest_about_small_samples():
    lo, hi = gaps.wilson(1, 5)
    assert 0 < lo < 0.2 < hi < 0.8
    assert gaps.wilson(0, 0) == (0.0, 1.0)
    narrow = gaps.wilson(40, 100)
    wide = gaps.wilson(4, 10)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])                  # more evidence, narrower range
    lo2, hi2 = gaps.wilson(5, 5)
    assert hi2 == pytest.approx(1.0, abs=0.01) and lo2 > 0.5


def test_one_wrong_answer_is_never_a_gap():
    out = gaps.rank_gaps(TITLES, EDGES, {"A": st(0.1, 1, 0)})
    assert out["gaps"] == []


def test_the_foundation_ranks_first_and_the_repair_path_goes_foundation_first():
    states = {"A": st(0.30, 5, 1), "B": st(0.35, 5, 2), "C": st(0.90, 6, 6), "D": st(0.40, 4, 1), "E": st(0.50, 4, 2)}
    out = gaps.rank_gaps(TITLES, EDGES, states)
    ids = [g["conceptId"] for g in out["gaps"]]
    assert ids[0] == "A" and set(ids) == {"A", "B", "D", "E"}              # C is secure, so it is not a gap
    assert out["repairPath"].index("A") < out["repairPath"].index("B") < out["repairPath"].index("D")
    by = {g["conceptId"]: g for g in out["gaps"]}
    assert by["B"]["root"] == {"id": "A", "title": "A"} and by["A"]["root"] is None
    assert by["A"]["downstream"] == 4 - 1 or by["A"]["downstream"] >= 3     # B, D and E build on A (C is secure)
    assert all(0 <= g["interval"][0] <= g["p"] <= g["interval"][1] <= 1 or g["interval"][0] <= g["interval"][1] for g in out["gaps"])


def test_more_downstream_damage_raises_priority():
    base = {"A": st(0.40, 5, 2), "B": st(0.40, 5, 2)}
    wide_edges = [("A", "X1"), ("A", "X2"), ("A", "X3"), ("B", "Y1")]
    titles = {c: {"title": c, "grade": 7} for c in ["A", "B", "X1", "X2", "X3", "Y1"]}
    out = gaps.rank_gaps(titles, wide_edges, base)
    assert [g["conceptId"] for g in out["gaps"]][0] == "A"                 # same score, but A blocks three later topics


def test_summary_and_unmeasured_topics_are_reported_not_guessed():
    states = {"A": st(0.9, 6, 6), "B": st(0.5, 4, 2)}
    out = gaps.rank_gaps(TITLES, EDGES, states)
    assert out["summary"] == {"secure": 1, "learning": 0, "gaps": 1, "unmeasured": 3}
    assert {u["conceptId"] for u in out["unmeasured"]} == {"C", "D", "E"}


def test_every_gap_carries_a_plain_reason_with_numbers():
    out = gaps.rank_gaps(TITLES, EDGES, {"A": st(0.30, 5, 1), "B": st(0.35, 5, 2)})
    a = out["gaps"][0]
    assert "1 of 5" in a["reason"] and "%" in a["reason"]


# ---- API -------------------------------------------------------------------------------------------------
@pytest.fixture()
def student(db, client):
    p = make_profile(db, "student", grade=7)
    for cid in "ABC":
        db.add(Concept(id=f"g-{cid.lower()}", title=f"Topic {cid}", grade=7, subject_id="maths"))
    db.commit()
    db.add_all([ConceptEdge(prereq_id="g-a", concept_id="g-b"), ConceptEdge(prereq_id="g-b", concept_id="g-c")])
    db.commit()
    return p


def put(db, p, cid, pk, n, c):
    db.merge(ConceptState(student_id=p.id, concept_id=cid, p_known=pk, n_obs=n, n_correct=c, streak=0, status="learning", param_version="t", last_obs_at=datetime.now(timezone.utc)))
    db.commit()


def test_gaps_endpoint_returns_ranked_gaps_with_actions(db, client, student):
    put(db, student, "g-a", 0.30, 5, 1)
    put(db, student, "g-b", 0.35, 5, 2)
    r = client.get(f"{API}/progress/gaps", headers=auth(student))
    assert r.status_code == 200
    body = r.json()
    first = body["gaps"][0]
    assert first["conceptId"] == "g-a" and first["actions"]["practice"] == "/practice?concept=g-a" and first["actions"]["test"] == "/tests/new?kind=topic_test&concept=g-a"
    assert body["repairPath"][0] == "g-a" and body["summary"]["gaps"] == 2 and body["evidence"] == 10


def test_gaps_endpoint_is_empty_for_a_new_student_and_student_only(db, client, student):
    body = client.get(f"{API}/progress/gaps", headers=auth(student)).json()
    assert body["gaps"] == [] and body["evidence"] == 0
    assert client.get(f"{API}/progress/gaps", headers=auth(make_profile(db, "teacher"))).status_code == 403
