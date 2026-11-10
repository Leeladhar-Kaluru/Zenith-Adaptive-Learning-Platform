import random

import pytest

from app.engine import bkt, elo, graph, grading, policy, selector


# ---- grading ---------------------------------------------------------------------------------
def test_numeric_accepts_unicode_minus_fractions_and_tolerance():
    spec = {"value": -3, "tolerance": 0}
    assert grading.grade("numeric", spec, {"value": "−3"}).correct
    assert grading.grade("numeric", spec, {"value": "-3.0"}).correct
    assert not grading.grade("numeric", spec, {"value": "3"}).correct
    assert grading.grade("numeric", {"value": "3/4"}, {"value": "0.75"}).correct
    assert grading.grade("numeric", {"value": 3.14, "tolerance": 0.01}, {"value": "3.145"}).correct
    assert not grading.grade("numeric", spec, {"value": "abc"}).correct
    assert not grading.grade("numeric", {"value": 1}, {"value": "1/0"}).correct


def test_mcq_multi_truefalse_fill_match():
    assert grading.grade("mcq", {"correct": "B"}, {"choice": "b"}).correct
    assert not grading.grade("mcq", {"correct": "B"}, {"choice": "A"}).correct
    g = grading.grade("multi", {"correct": ["A", "C"]}, {"choices": ["A"]})
    assert not g.correct and 0 < g.score < 1
    assert grading.grade("multi", {"correct": ["A", "C"]}, {"choices": ["C", "A"]}).correct
    assert grading.grade("truefalse", {"correct": True}, {"choice": "true"}).correct
    assert not grading.grade("truefalse", {"correct": True}, {"choice": False}).correct
    assert grading.grade("fill", {"accepted": ["integers"]}, {"text": "  Integers "}).correct
    m = grading.grade("match", {"pairs": {"a": "1", "b": "2"}}, {"pairs": {"a": "1", "b": "9"}})
    assert not m.correct and m.score == 0.5


def test_public_payload_never_contains_the_answer():
    assert "correct" not in grading.public_payload("mcq", {"options": [], "correct": "A"})


# ---- BKT -------------------------------------------------------------------------------------
def test_bkt_correct_raises_and_incorrect_lowers_belief():
    p = 0.4
    up = bkt.update(p, correct=True, kind="mcq", n_options=4, difficulty="standard", hints_used=0)
    down = bkt.update(p, correct=False, kind="mcq", n_options=4, difficulty="standard", hints_used=0)
    assert up > p > down


def test_bkt_numeric_correct_is_stronger_evidence_than_guessable_mcq():
    num = bkt.update(0.3, correct=True, kind="numeric", n_options=0, difficulty="standard", hints_used=0)
    mcq = bkt.update(0.3, correct=True, kind="mcq", n_options=4, difficulty="standard", hints_used=0)
    assert num > mcq


def test_bkt_hinted_correct_is_weaker_than_unaided_correct():
    aided = bkt.update(0.3, correct=True, kind="mcq", n_options=4, difficulty="standard", hints_used=2)
    clean = bkt.update(0.3, correct=True, kind="mcq", n_options=4, difficulty="standard", hints_used=0)
    assert aided < clean


def test_bkt_weight_blends_toward_prior():
    full = bkt.update(0.3, correct=True, kind="mcq", n_options=4, difficulty="standard", hints_used=0, weight=1.0)
    half = bkt.update(0.3, correct=True, kind="mcq", n_options=4, difficulty="standard", hints_used=0, weight=0.5)
    assert 0.3 < half < full


def test_one_lucky_answer_never_makes_a_concept_secure():
    p = bkt.update(bkt.P_INIT, correct=True, kind="mcq", n_options=4, difficulty="standard", hints_used=0)
    assert bkt.status(p, 1, 1) == "unassessed"


def test_a_single_wrong_answer_never_confirms_a_gap():
    p = bkt.update(bkt.P_INIT, correct=False, kind="mcq", n_options=4, difficulty="standard", hints_used=0)
    assert bkt.status(p, 1, 0) == "unassessed"


def test_status_secure_needs_evidence_and_probability():
    p = bkt.P_INIT
    for _ in range(6):
        p = bkt.update(p, correct=True, kind="numeric", n_options=0, difficulty="standard", hints_used=0)
    assert p > 0.85 and bkt.status(p, 6, 6) == "secure"
    assert bkt.status(0.9, 2, 2) == "unassessed"


def test_status_gap_confirmed_after_repeated_misses():
    p = bkt.P_INIT
    for _ in range(5):
        p = bkt.update(p, correct=False, kind="mcq", n_options=4, difficulty="standard", hints_used=0)
    assert bkt.status(p, 5, 0) == "gap_confirmed"


def test_level_rises_only_with_evidence():
    assert bkt.level(0.9, 1) == 1
    assert bkt.level(0.5, 5) == 2
    assert bkt.level(0.8, 6) == 3


# ---- Elo -------------------------------------------------------------------------------------
def test_elo_moves_the_right_way_and_is_bounded():
    t, b = elo.update(0.0, 0.0, True, 0, 0)
    assert t > 0 and b < 0
    t2, b2 = elo.update(0.0, 0.0, False, 0, 0)
    assert t2 < 0 and b2 > 0
    assert abs(elo.update(0.0, 0.0, True, 1000, 1000)[0]) < abs(t)


def test_elo_expected_is_a_probability():
    assert elo.expected(0, 0) == pytest.approx(0.5)
    assert elo.expected(3, 0) > 0.9 > 0.1 > elo.expected(-3, 0)


# ---- graph -----------------------------------------------------------------------------------
EDGES = [("whole", "integers"), ("integers", "expr"), ("expr", "equations"), ("integers", "equations")]


def test_topological_order_and_cycle_detection():
    order = graph.topological_order(["whole", "integers", "expr", "equations"], EDGES)
    assert order.index("whole") < order.index("integers") < order.index("equations")
    with pytest.raises(graph.CycleError):
        graph.topological_order(["a", "b"], [("a", "b"), ("b", "a")])
    with pytest.raises(ValueError):
        graph.topological_order(["a"], [("a", "zzz")])


def test_ancestors_depth_and_descendants():
    anc = dict(graph.ancestors("equations", EDGES, depth=3))
    assert anc["integers"] == 1 and anc["expr"] == 1 and anc["whole"] == 2
    assert dict(graph.ancestors("equations", EDGES, depth=1)).get("whole") is None
    assert graph.descendants("integers", EDGES) == {"expr", "equations"}


def test_investigate_probes_unknown_and_finds_root_gap():
    state = {"expr": {"p": 0.3, "n": 4, "status": "gap_confirmed"}, "integers": {"p": 0.2, "n": 4, "status": "gap_confirmed"}}
    res = graph.investigate("equations", EDGES, state)
    assert res["root"] == "integers" or res["root"] == "whole"
    state2 = {"integers": {"p": 0.9, "n": 5, "status": "secure"}}
    res2 = graph.investigate("equations", EDGES, state2)
    assert "expr" in res2["probe"] and res2["root"] is None


def test_investigate_does_not_confirm_with_one_answer():
    res = graph.investigate("equations", EDGES, {"integers": {"p": 0.1, "n": 1, "status": "gap_suspected"}})
    assert res["root"] is None and "integers" in res["probe"]


# ---- selector --------------------------------------------------------------------------------
def _cand(i, diff, beta, concept="c1"):
    return {"id": i, "difficulty": diff, "beta": beta, "concepts": [(concept, 1.0)]}


def test_selector_matches_item_difficulty_to_ability():
    cands = [_cand("easy", "intro", -1.0), _cand("mid", "standard", 0.0), _cand("hard", "challenge", 1.0)]
    states = {"c1": {"p": 0.7, "n": 5}}
    weak = selector.choose_item(cands, theta=-1.2, states={"c1": {"p": 0.3, "n": 5}}, recent_ids=set(), rng=random.Random(1))
    strong = selector.choose_item(cands, theta=1.5, states=states, recent_ids=set(), rng=random.Random(1))
    assert weak["id"] in ("easy", "mid") and strong["id"] in ("mid", "hard")
    assert weak["id"] != "hard"


def test_selector_locks_challenge_until_evidence_and_skips_trivial_when_secure():
    cands = [_cand("mid", "standard", 0.0), _cand("hard", "challenge", 1.0)]
    low = selector.choose_item(cands, theta=2.0, states={"c1": {"p": 0.3, "n": 2}}, recent_ids=set(), rng=random.Random(2))
    assert low["id"] == "mid"
    cands2 = [_cand("easy", "intro", -1.0), _cand("hard", "challenge", 1.0)]
    sec = selector.choose_item(cands2, theta=0.0, states={"c1": {"p": 0.92, "n": 8}}, recent_ids=set(), rng=random.Random(2))
    assert sec["id"] == "hard"


def test_selector_avoids_recent_items_unless_nothing_else():
    cands = [_cand("a", "standard", 0.0), _cand("b", "standard", 0.0)]
    pick = selector.choose_item(cands, 0.0, {}, {"a"}, rng=random.Random(3))
    assert pick["id"] == "b"
    assert selector.choose_item(cands[:1], 0.0, {}, {"a"}, rng=random.Random(3))["id"] == "a"
    assert selector.choose_item([], 0.0, {}, set()) is None


# ---- policy ----------------------------------------------------------------------------------
def test_policy_prefers_prerequisite_over_new_content_and_explains_itself():
    a = policy.step("next_lesson", "lesson", "Adding integers", "next in chapter", "/l/1", 10)
    b = policy.step("prereq", "prereq", "Counting backwards", "gap found", "/l/0", 5, evidence=4)
    assert policy.pick([a, b])["title"] == "Counting backwards"
    assert policy.pick([]) is None
    assert policy.pick([b])["evidenceCount"] == 4
