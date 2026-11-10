import re

import pytest
from sympy import Eq, solve, symbols, sympify

from app.engine import grading
from app.engine.templates import REGISTRY, InvalidInstance, base, generate, templates_for

FAMILIES = {"area_rect", "perimeter_rect", "square_of", "square_root", "frac_compare", "int_add", "int_subtract", "int_compare", "int_hops", "eq_one_step", "eq_two_step", "eq_word", "eq_both_sides"}


def test_all_families_registered():
    assert FAMILIES <= set(REGISTRY)
    assert templates_for("integers-add")


def test_same_seed_same_instance_and_seeds_vary():
    assert generate("eq_two_step", 7, 3) == generate("eq_two_step", 7, 3)
    assert len({generate("eq_two_step", s, 3).stem for s in range(30)}) > 10


def test_unknown_template_and_bad_level():
    with pytest.raises(KeyError):
        generate("nope", 1, 1)
    with pytest.raises(ValueError):
        generate("int_add", 1, 6)


@pytest.mark.parametrize("tid", sorted(FAMILIES))
def test_every_level_and_seed_is_valid_under_the_real_grader(tid):
    for level in range(1, 6):
        for seed in range(150):
            inst = generate(tid, seed, level)
            right = inst.answer_spec["correct"]
            wrongs = [o["key"] for o in inst.payload["options"] if o["key"] != right]
            assert len(inst.payload["options"]) >= 3 and wrongs
            assert grading.grade("mcq", inst.answer_spec, {"choice": right}).correct
            assert not any(grading.grade("mcq", inst.answer_spec, {"choice": k}).correct for k in wrongs)
            assert set(inst.misconceptions) <= set(wrongs)


def test_equation_answers_agree_with_sympy():
    x = symbols("x")
    for tid in ("eq_one_step", "eq_two_step", "eq_both_sides"):
        for level in range(1, 6):
            for seed in range(60):
                inst = generate(tid, seed, level)
                text = inst.stem.split(":", 1)[1].replace("−", "-")
                left, right = (re.sub(r"(\d)x", r"\1*x", side) for side in text.split("="))
                sol = solve(Eq(sympify(left), sympify(right)), x)[0]
                key = inst.answer_spec["correct"]
                shown = next(o["text"] for o in inst.payload["options"] if o["key"] == key).replace("−", "-")
                assert sol == sympify(shown), (tid, level, seed, inst.stem)


def test_difficulty_grows_with_level():
    def size(tid, level):
        nums = [int(n) for s in range(80) for n in re.findall(r"\d+", generate(tid, s, level).stem)]
        return sum(nums) / len(nums)
    for tid in ("int_add", "eq_one_step", "eq_two_step"):
        assert size(tid, 5) > size(tid, 1)


def test_bad_template_is_rejected():
    class Bad:
        id, version, concept = "bad_t", 1, "x"

        def make(self, rng, level):
            payload, spec, mis = base.mcq("1", [("2", None), ("3", None)], rng)
            spec["correct"] = "Z"                    # declares an answer that is not an option
            return base.Instance("", 0, 0, 0, "mcq", "?", payload, spec, "", [], "x", mis)

    base.register(Bad())
    try:
        with pytest.raises(InvalidInstance):
            generate("bad_t", 1, 1)
    finally:
        del REGISTRY["bad_t"]
