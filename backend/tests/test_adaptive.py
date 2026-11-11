import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.engine import adaptive, retention
from app.models import ConceptState, Item
from tests.test_api import API, world  # noqa: F401  (the published sample content)


def test_the_ability_estimate_rises_with_right_answers_and_the_error_shrinks_with_more_of_them():
    right = [(0.0, True)] * 6
    wrong = [(0.0, False)] * 6
    t_hi, se_hi = adaptive.estimate(right)
    t_lo, se_lo = adaptive.estimate(wrong)
    assert t_hi > 0.5 > -0.5 > t_lo and abs(t_hi + t_lo) < 1e-6                         # symmetric
    t0, se0 = adaptive.estimate([])
    assert (t0, round(se0, 3)) == (0.0, 1.0) and se_hi < se0                                # no answers: the prior, fully uncertain
    assert adaptive.estimate(right * 3)[1] < se_hi                                          # more evidence, tighter estimate
    mixed = [(-1.0, True), (0.0, True), (1.0, False), (2.0, False)]
    t, _ = adaptive.estimate(mixed)
    assert -0.5 < t < 1.5


def test_the_next_question_is_the_most_informative_and_untouched_topics_get_a_nudge():
    cands = [{"id": "a", "beta": -2.0, "concepts": [("x", 1.0)]}, {"id": "b", "beta": 0.1, "concepts": [("x", 1.0)]}, {"id": "c", "beta": 0.1, "concepts": [("y", 1.0)]}]
    assert adaptive.choose(cands, 0.0, {})["id"] in ("b", "c")                               # near the estimate beats far away
    assert adaptive.choose(cands, 0.0, {"x": 3})["id"] == "c"                                # x has been asked a lot: prefer y
    assert adaptive.choose([], 0.0, {}) is None
    assert adaptive.should_stop(5, 0.3, 10) == (False, "")                                   # never before the minimum
    assert adaptive.should_stop(6, 0.5, 10)[0] and adaptive.should_stop(12, 0.9, 10)[0] and adaptive.should_stop(2, 0.9, 0)[0]
    lo, hi = adaptive.interval(0.4, 0.5)
    assert round(hi - lo, 2) == round(2 * 1.645 * 0.5, 2)


def test_predicted_recall_fades_with_time_and_slowly_for_well_practised_topics():
    now = datetime(2026, 11, 11, tzinfo=timezone.utc)
    week_ago = now - timedelta(days=7)
    few = retention.recall(0.9, 3, week_ago, now)
    many = retention.recall(0.9, 20, week_ago, now)
    assert 0 < few < many < 0.9 and retention.recall(0.9, 3, now, now) == 0.9 and retention.recall(0.9, 3, None, now) == 0.9
    d = retention.days_until(0.9, 5, now, retention.FADING_BELOW, now)
    assert d is not None and math.isclose(retention.recall(0.9, 5, now, now + timedelta(days=d)), retention.FADING_BELOW, rel_tol=1e-6)
    assert retention.days_until(0.4, 5, now, 0.55, now) is None


def test_the_adaptive_check_stops_early_never_repeats_a_question_and_reports_a_range(client, db, world):
    h = world["h"]
    since = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    seen: set[str] = set()
    out = None
    for _ in range(14):
        out = client.get(f"{API}/adaptive/step", params={"since": since, "concept": "number-line"}, headers=h).json()
        if out["done"]:
            break
        q = out["item"]
        assert q["id"] not in seen
        seen.add(q["id"])
        item = db.get(Item, q["id"])
        spec = item.answer_spec
        resp = {"choice": spec["correct"]} if item.kind == "mcq" else {"value": spec.get("value")} if item.kind == "numeric" else {"choice": bool(spec.get("correct"))}
        r = client.post(f"{API}/evidence", json={"itemId": q["id"], "response": resp, "hintsUsed": 0, "ms": 3000, "context": "probe", "clientEventId": uuid.uuid4().hex}, headers=h)
        assert r.status_code == 200, r.text
    assert out["done"] and out["answered"] == len(seen) and out["answered"] <= adaptive.MAX_ITEMS and out["reason"]
    lo, hi = out["interval"]
    assert lo < out["ability"] < hi and out["topics"] and out["right"] == out["answered"] and out["model"] == adaptive.MODEL_VERSION


def test_a_fading_topic_shows_on_the_dashboard_with_its_inputs(client, db, world):
    from app.models import Concept
    cid = db.scalar(select(Concept.id).limit(1))
    db.add(ConceptState(student_id=world["student"].id, concept_id=cid, p_known=0.9, n_obs=4, n_correct=4, streak=4, status="secure", param_version="prior-v1",
                        last_obs_at=datetime.now(timezone.utc) - timedelta(days=40)))
    db.commit()
    d = client.get(f"{API}/profile/dashboard", headers=world["h"]).json()
    assert d["retentionModel"] == retention.MODEL_VERSION and d["fading"] and d["fading"][0]["id"] == cid and d["fading"][0]["recall"] < 0.55
