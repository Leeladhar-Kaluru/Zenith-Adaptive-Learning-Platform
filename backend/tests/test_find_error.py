import re
import uuid

import pytest
from sqlalchemy import select
from sympy import Eq, solve, symbols, sympify

from app.cms.schema import ItemDef
from app.engine import grading
from app.engine.templates import generate
from app.models import ConceptLevel, Item
from app.services import generator, items as item_svc
from tests.conftest import auth, make_profile

API = "/api/v1"
CONCEPT = "simple-equation-two-step"
X = symbols("x")


def eq_solution(step: str):
    text = step.split(": ")[-1] if ": " in step else step.replace("Start with ", "")
    text = text.replace("−", "-")
    left, right = (re.sub(r"(\d)x", r"\1*x", side) for side in text.split("="))
    return solve(Eq(sympify(left), sympify(right)), X)[0]


def test_grading_picks_the_wrong_step_only():
    spec = {"wrong_step": 1}
    assert grading.grade("find_error", spec, {"step": 1}).correct
    assert not grading.grade("find_error", spec, {"step": 2}).correct
    assert grading.grade("find_error", spec, {"step": 1}).reveal == 1
    for bad in ({"step": "abc"}, {"step": None}, {}):
        with pytest.raises((ValueError, TypeError, KeyError)):
            grading.grade("find_error", spec, bad)


def test_item_schema_checks_steps_and_index():
    base = dict(key="k", kind="find_error", stem="Find the wrong step", difficulty="standard", purpose="practice", concepts=[{"id": "c"}], explanation="e", hints=["h"])
    ItemDef(**base, steps=["a", "b", "c"], wrong_step=1)
    with pytest.raises(ValueError):
        ItemDef(**base, steps=["a", "b"], wrong_step=1)
    with pytest.raises(ValueError):
        ItemDef(**base, steps=["a", "b", "c"], wrong_step=3)
    with pytest.raises(ValueError):
        ItemDef(**base, steps=["a", "b", "c"], wrong_step=0)          # the first line is the given problem, never the mistake


@pytest.mark.parametrize("level", [3, 4, 5])
def test_every_generated_solution_has_exactly_one_wrong_step(level):
    for seed in range(120):
        inst = generate("eq_find_error", seed, level)
        steps, wrong = inst.payload["steps"], inst.answer_spec["wrong_step"]
        assert inst.kind == "find_error" and len(steps) >= 3 and 1 <= wrong < len(steps)
        # A line is wrong when it does not follow from the line before it (same solution). Lines that correctly follow a
        # mistaken line are not "the mistake": the student must find the first line where the solution changes.
        breaks = [i for i in range(1, len(steps)) if eq_solution(steps[i]) != eq_solution(steps[i - 1])]
        assert breaks == [wrong], (seed, level, steps, breaks)


def test_the_answer_is_never_sent_to_the_student(db):
    from app.models import Concept
    make_profile(db, "student")                              # also creates the board and subjects the concept belongs to
    if not db.get(Concept, CONCEPT):
        db.add(Concept(id=CONCEPT, title="Two-step equations", grade=7, subject_id="maths"))
        db.commit()
    inst = generate("eq_find_error", 7, 3)
    item = generator.materialise(db, inst)
    pub = item_svc.public_item(item)
    assert pub["kind"] == "find_error" and pub["steps"] == inst.payload["steps"]
    assert "wrong_step" not in str(pub) and "correct" not in pub


@pytest.fixture()
def student(db, client):
    from app.models import Concept
    p = make_profile(db, "student", grade=7)
    if not db.get(Concept, CONCEPT):
        db.add(Concept(id=CONCEPT, title="Two-step equations", grade=7, subject_id="maths"))
        db.commit()
    return p


def kinds_served(client, p, n=40):
    return [client.get(f"{API}/practice/next", params={"concept": CONCEPT}, headers=auth(p)).json()["item"]["kind"] for _ in range(n)]


def test_detective_questions_appear_from_level_three_and_not_before(db, client, student):
    assert "find_error" not in kinds_served(client, student)                  # level 1: never
    db.add(ConceptLevel(student_id=student.id, concept_id=CONCEPT, level=3, streak_up=0, streak_down=0, reason=""))
    db.commit()
    got = kinds_served(client, student)
    assert "find_error" in got and "mcq" in got                               # a mix, not only detective questions


def test_answering_a_detective_question_is_graded_and_moves_the_ladder(db, client, student):
    db.add(ConceptLevel(student_id=student.id, concept_id=CONCEPT, level=3, streak_up=0, streak_down=0, reason=""))
    db.commit()
    for _ in range(40):
        served = client.get(f"{API}/practice/next", params={"concept": CONCEPT}, headers=auth(student)).json()
        if served["item"]["kind"] == "find_error":
            break
    item = db.get(Item, uuid.UUID(served["item"]["id"]))
    r = client.post(f"{API}/evidence", headers=auth(student), json={"itemId": str(item.id), "response": {"step": item.answer_spec["wrong_step"]}, "hintsUsed": 0,
                                                                     "ms": 9000, "context": "solve", "clientEventId": uuid.uuid4().hex}).json()
    assert r["correct"] is True and r["feedback"]
    wrong = next(i for i in range(len(item.payload["steps"])) if i != item.answer_spec["wrong_step"])
    served2 = client.post(f"{API}/evidence", headers=auth(student), json={"itemId": str(item.id), "response": {"step": wrong}, "hintsUsed": 0, "ms": 9000,
                                                                          "context": "solve", "clientEventId": uuid.uuid4().hex}).json()
    assert served2["correct"] is False
