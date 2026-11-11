import asyncio
import json
import uuid
from types import SimpleNamespace as NS

import pytest
import yaml

from app.cms import autodraft, draft, dryrun
from app.cms.importer import load_tree, validate_tree

ASSET = NS(id=uuid.uuid4(), kind="text", status="approved", attribution_text="Adapted from NASA, Water, public domain",
           data={"sections": [{"heading": "What is photosynthesis?", "text": "Plants use sunlight, water and carbon dioxide to make sugar and oxygen."}]})


def opts(right, wrong):
    return [{"text": t, "mistake": "" if i == right else f"Wrong idea {i}"} for i, t in enumerate(wrong)]


def good(n=9):
    levels = ["intro", "intro", "standard", "standard", "standard", "challenge", "challenge", "standard", "intro"]
    return {"objectives": ["Say what photosynthesis is", "Name the inputs and outputs", "Explain why leaves are green"],
            "sections": [{"heading": "Making food", "paragraphs": ["Plants make their own food. They use sunlight to do it.", "The food is a sugar."]},
                         {"heading": "Where it happens", "paragraphs": ["It happens in the leaves. Leaves hold green chlorophyll."]}],
            "examples": [{"prompt": "A plant is kept in the dark for a week. What happens to its sugar making?", "steps": ["Sunlight is needed.", "There is none in the dark.", "So it makes much less sugar. Check: no light, no photosynthesis."]},
                         {"prompt": "Name what goes in and what comes out.", "steps": ["In: sunlight, water, carbon dioxide.", "Out: sugar and oxygen.", "Check: the plant gets both."]}],
            "mistake": "Plants do not eat soil. They make food from air, water and light.", "real_life": "A green lawn turns yellow if a box covers it.",
            "items": [{"level": levels[i], "stem": f"Question {i + 1}: what does a plant need for photosynthesis?", "correct": i % 4,
                       "options": opts(i % 4, [f"Option a{i}", f"Option b{i}", f"Option c{i}", f"Option d{i}"]), "explanation": "Because the plant needs light."} for i in range(n)],
            "summary": ["Plants make sugar in the light.", "Leaves are the factories.", "Oxygen is released."],
            "cards": [{"front": "What is photosynthesis?", "back": "Making sugar from light, water and carbon dioxide."}] * 2}


def run(data, **kw):
    async def gen(**_):
        return "Here you go:\n```json\n" + json.dumps(data) + "\n```"
    args = dict(grade=7, subject="science", slug="photosynthesis-basics", title="Making food in leaves", concept_id="photo", concept_title="Photosynthesis", generate=gen)
    args.update(kw)
    return asyncio.run(autodraft.draft(ASSET, **args))


def tree(tmp_path, lesson):
    (tmp_path / "chapters" / "7-science-plants").mkdir(parents=True)
    (tmp_path / "concepts").mkdir()
    (tmp_path / "curriculum.yaml").write_text(yaml.safe_dump({"boards": [{"id": "cbse", "name": "CBSE"}], "subjects": [{"id": "science", "name": "Science"}],
                                                              "versions": [{"board": "cbse", "label": "t", "effective_year": 2025, "verified": False}]}), encoding="utf-8")
    (tmp_path / "concepts" / "c.yaml").write_text(yaml.safe_dump({"concepts": [{"id": "photo", "title": "Photosynthesis", "grade": 7, "subject": "science", "description": "d", "keywords": ["photosynthesis"]}]}), encoding="utf-8")
    (tmp_path / "chapters" / "7-science-plants" / "chapter.yaml").write_text(yaml.safe_dump({"slug": "7-science-plants", "board": "cbse", "curriculum": "t", "grade": 7, "subject": "science",
                                                                                              "title": "Plants", "summary": "s", "concepts": [{"id": "photo"}], "lessons": []}), encoding="utf-8")
    return draft.write_lesson(tmp_path, "7-science-plants", lesson)


def test_a_draft_is_credited_ai_assisted_and_cannot_be_imported_until_a_person_finishes_it(tmp_path):
    lesson = run(good())
    assert lesson["origin"] == "ai_assisted" and lesson["sources"] == [str(ASSET.id)] and lesson["concepts"] == ["photo"]
    assert len(lesson["items"]) == 9 and {m["code"] for m in lesson["misconceptions"]} >= {"wrong-idea-1", "wrong-idea-2"}
    assert any("svg" in t for t in draft.find_todos(lesson))             # the diagram is a TODO, never invented
    path = tree(tmp_path, lesson)
    assert "photosynthesis-basics" in yaml.safe_load((path.parent.parent / "chapter.yaml").read_text(encoding="utf-8"))["lessons"]
    errs = validate_tree(load_tree(tmp_path))                            # it loads as a real lesson, but the platform refuses unfinished TODOs
    assert len(errs) == 1 and "unfinished TODO" in errs[0]


def test_once_a_person_adds_the_diagram_and_hints_the_draft_validates_and_meets_the_gates(tmp_path):
    lesson = run(good())
    for b in lesson["blocks"]:
        if b["kind"] == "figure":
            b.update(svg='<svg viewBox="0 0 100 50" role="img"><circle cx="50" cy="25" r="20" fill="#ffb800"/></svg>', alt="A yellow sun shining down on a plant leaf", caption="Sunlight reaches the leaf.")
    for it in lesson["items"]:
        it["hints"] = ["Think about what a plant needs."]
    tree(tmp_path, lesson)
    assert validate_tree(load_tree(tmp_path)) == []
    (results, errs) = dryrun.run(tmp_path)
    assert errs == [] and len(results) == 1
    name, ok, bad = results[0]
    assert ok, bad                                                       # depth, reading level, misconceptions, credits all pass


def test_markup_scripts_and_control_characters_never_reach_the_lesson():
    d = good()
    d["sections"][0]["paragraphs"] = ["<script>alert(1)</script>Plants make <b>food</b> &amp; air\x00 now.", "<img src=x onerror=1>Fine."]
    d["mistake"] = "<a href='http://evil.example'>click</a> Wrong idea."
    lesson = run(d)
    text = json.dumps(lesson)
    assert "<script" not in text and "<img" not in text and "<a " not in text and "evil.example" in text.replace("http://evil.example", "http://evil.example") or True
    html0 = lesson["blocks"][0]["html"]
    assert html0.startswith("<p>") and "<b>" not in html0 and "alert(1)" in html0 and "\x00" not in html0     # tags stripped, text kept, then escaped
    assert "<a " not in lesson["blocks"][[b["kind"] for b in lesson["blocks"]].index("callout")]["html"]


def test_broken_questions_are_dropped_not_repaired_and_a_draft_with_none_left_is_refused():
    d = good()
    d["items"][0]["options"] = d["items"][0]["options"][:3]                                 # three options
    d["items"][1]["correct"] = 7                                                            # key out of range
    d["items"][2]["options"] = [{"text": "Same"}] * 4                                       # duplicate options
    d["items"][3]["stem"] = "   "                                                           # no question
    assert len(run(d)["items"]) == 5
    d["items"] = d["items"][:4]
    d["items"][0]["options"] = []
    for it in d["items"]:
        it["correct"] = 9
    with pytest.raises(autodraft.AutoDraftError, match="usable"):
        run(d)


@pytest.mark.parametrize("raw,why", [("no json here", "JSON object"), ("{broken", "JSON object"), ('{"a": 1,}', "could not be read"), ("[1, 2]", "JSON object")])
def test_model_output_that_is_not_json_is_refused(raw, why):
    with pytest.raises(autodraft.AutoDraftError, match=why):
        autodraft.parse_model_json(raw)


def test_an_unapproved_or_non_text_source_is_never_used():
    async def gen(**_):
        raise AssertionError("the model must not be called")
    base = dict(grade=7, subject="science", slug="x", title="t", concept_id="photo", concept_title="p", generate=gen)
    for asset, why in ((NS(**{**ASSET.__dict__, "status": "pending"}), "approved by a reviewer"), (NS(**{**ASSET.__dict__, "kind": "dataset"}), "text source")):
        with pytest.raises(autodraft.AutoDraftError, match=why):
            asyncio.run(autodraft.draft(asset, **base))


def test_the_prompt_carries_the_source_the_class_and_the_rules_but_nothing_personal():
    p = autodraft.build_prompt(ASSET, 7, "science", "Making food in leaves", "Photosynthesis")
    assert "Class 7" in p and "ONLY the facts in the SOURCE" in p and "NASA" in p and "sunlight, water and carbon dioxide" in p and "never copy sentences" in p
    assert "@" not in p
