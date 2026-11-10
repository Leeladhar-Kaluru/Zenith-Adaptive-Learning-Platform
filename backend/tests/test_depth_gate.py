from app.cms import gates


def lesson(**over):
    blocks = [
        {"kind": "text", "html": "<p>Idea.</p>"},
        {"kind": "example", "heading": "A", "prompt": "p", "steps": ["1", "2", "3"]},
        {"kind": "figure", "svg": "<svg/>", "alt": "A figure alt text", "caption": ""},
        {"kind": "check", "item": "q1"},
        {"kind": "summary", "points": ["a", "b", "c"]},
    ]
    items = [{"key": f"q{i}", "kind": "mcq", "difficulty": d, "purpose": "practice", "concepts": [{"id": "c"}],
              "options": [{"key": "A", "text": "1"}, {"key": "B", "text": "2", "misconception": "m1"}, {"key": "C", "text": "3", "misconception": "m2"}], "correct": "A"}
             for i, d in enumerate(["intro", "intro", "standard", "standard", "standard", "standard", "challenge", "challenge"], start=1)]
    kw = dict(title="t", grade=6, objectives=["o"], blocks=blocks, items=items, concept_ids={"c"}, known_concepts={"c"}, graph_error=None,
              curriculum_verified=True, misconception_codes={"m1", "m2"})
    kw.update(over)
    return next(g for g in gates.lesson_gates(**kw) if g.name == "Lesson has enough depth")


def test_a_full_lesson_passes():
    assert lesson().passed


def test_each_missing_part_is_named():
    base = lesson().__class__
    full = lesson(); assert full.passed
    thin_blocks = [{"kind": "text", "html": "x"}, {"kind": "check", "item": "q1"}, {"kind": "summary", "points": ["a"]}]
    g = lesson(blocks=thin_blocks)
    assert not g.passed
    for needle in ("worked example", "figure or simulation", "recap"):
        assert needle in g.detail


def test_question_count_and_difficulty_spread_are_checked():
    items = [{"key": "q1", "kind": "mcq", "difficulty": "standard", "purpose": "practice", "concepts": [{"id": "c"}],
              "options": [{"key": "A", "text": "1"}, {"key": "B", "text": "2", "misconception": "m1"}, {"key": "C", "text": "3"}], "correct": "A"}] * 3
    g = lesson(items=items)
    assert not g.passed and "at least 8 questions" in g.detail and "intro" in g.detail and "challenge" in g.detail and "misconception" in g.detail


def test_one_longer_example_counts_in_place_of_two():
    one = [{"kind": "text", "html": "x"}, {"kind": "example", "heading": "A", "prompt": "p", "steps": ["1", "2", "3"]},
           {"kind": "widget", "widget": "sim_equation", "config": {}, "task": "t"}, {"kind": "check", "item": "q1"}, {"kind": "summary", "points": ["a", "b", "c"]}]
    assert lesson(blocks=one).passed
    short = [dict(b) for b in one]
    short[1] = {"kind": "example", "heading": "A", "prompt": "p", "steps": ["1", "2"]}
    assert not lesson(blocks=short).passed
