"""Builds a small but realistic content tree on disk for tests. Mirrors the real authoring format."""
from pathlib import Path

import yaml

SVG = '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>'


def item(key, stem, correct_text, wrong, concept, *, difficulty="standard", purpose="practice", verify=None, misc=None):
    texts = [correct_text] + wrong
    keys = "ABCD"[: len(texts)]
    return {
        "key": key, "kind": "mcq", "stem": stem, "difficulty": difficulty, "purpose": purpose,
        "concepts": [{"id": concept}], "explanation": f"The answer is {correct_text}.", "hints": ["Think about direction on the line."],
        "options": [{"key": k, "text": t, **({"misconception": misc} if (misc and i == 1) else {})} for i, (k, t) in enumerate(zip(keys, texts))],
        "correct": "A", **({"verify": verify} if verify else {}),
    }


def _pad_items(slug, concept, existing):
    """Enough extra questions that a fixture lesson meets the depth standard (8 questions, every difficulty, two tagged mistakes)."""
    out = []
    have = {i["difficulty"] for i in existing}
    for n, d in enumerate(["intro", "standard", "challenge", "standard", "intro", "challenge", "standard", "standard"]):
        if len(existing) + len(out) >= 8 and d in have:
            break
        it = item(f"{slug}-pad{n}", f"Practice question {n} on {concept}?", "right", ["wrong one", "wrong two"], concept, difficulty=d, purpose="practice", misc="pad-mistake")
        it["options"][2]["misconception"] = "reverses-subtraction"
        out.append(it)
        have.add(d)
    return out


def lesson(slug, title, concept, items, minutes=10):
    items = items + _pad_items(slug, concept, items)
    blocks = [
        {"kind": "text", "heading": "Idea", "html": "<p>Numbers can be less than zero. We show them on a line.</p>"},
        {"kind": "example", "heading": "Worked example", "prompt": "Move from 2 to -1.", "steps": ["Start at 2.", "Move 3 steps left.", "You land on -1."]},
        {"kind": "figure", "svg": SVG, "alt": "A circle used as a placeholder diagram", "caption": "A figure."},
        {"kind": "check", "item": items[0]["key"]},
        {"kind": "summary", "points": ["Negative numbers are left of zero.", "Left means smaller.", "Check by counting steps."]},
    ]
    return {"slug": slug, "title": title, "minutes": minutes, "objectives": ["Place integers on a number line"], "concepts": [concept],
            "blocks": blocks, "items": items,
            "misconceptions": [{"code": "reverses-subtraction", "concept": concept, "description": "Subtracts the smaller from the larger and ignores direction."},
                                          {"code": "pad-mistake", "concept": concept, "description": "A second common mistake used to give the fixture lesson enough depth."}]}


def build(root: Path, *, verified=False, bad_answer=False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "curriculum.yaml").write_text(yaml.safe_dump({
        "boards": [{"id": "cbse", "name": "CBSE"}], "subjects": [{"id": "maths", "name": "Mathematics"}],
        "versions": [{"board": "cbse", "label": "NCERT test", "effective_year": 2025, "verified": verified}]}), encoding="utf-8")
    (root / "concepts").mkdir(exist_ok=True)
    (root / "concepts" / "maths.yaml").write_text(yaml.safe_dump({"concepts": [
        {"id": "whole-numbers", "title": "Whole numbers", "grade": 6, "subject": "maths"},
        {"id": "number-line", "title": "Number line", "grade": 6, "subject": "maths", "prerequisites": [{"id": "whole-numbers", "why": "counting"}]},
        {"id": "adding-integers", "title": "Adding integers", "grade": 7, "subject": "maths", "prerequisites": [{"id": "number-line"}]},
    ]}), encoding="utf-8")
    d = root / "chapters" / "7-maths-integers"
    (d / "lessons").mkdir(parents=True, exist_ok=True)
    (d / "chapter.yaml").write_text(yaml.safe_dump({
        "slug": "7-maths-integers", "board": "cbse", "curriculum": "NCERT test", "grade": 7, "subject": "maths", "title": "Integers",
        "summary": "Numbers on both sides of zero.", "concepts": [{"id": "number-line"}, {"id": "adding-integers"}, {"id": "whole-numbers", "role": "foundation"}],
        "lessons": ["line", "adding"]}), encoding="utf-8")
    wrong_ans = "-7" if not bad_answer else "-3"
    l1_items = [
        item("q-line-1", "What is 2 - 5?", "-3", [wrong_ans, "3", "7"], "number-line", verify="2-5", misc="reverses-subtraction"),
        item("q-line-2", "Which is smaller: -4 or -1?", "-4", ["-1", "0", "1"], "number-line", difficulty="intro", purpose="practice"),
        item("q-line-3", "What is -6 + 6?", "0", ["12", "-12", "6"], "number-line", difficulty="standard", purpose="test", verify="-6+6"),
        item("q-line-4", "What is -10 - (-4)?", "-6", ["-14", "14", "6"], "number-line", difficulty="challenge", purpose="practice", verify="-10-(-4)"),
    ]
    l2_items = [
        item("q-add-1", "What is -3 + 5?", "2", ["-2", "8", "-8"], "adding-integers", verify="-3+5", misc="reverses-subtraction"),
        item("q-add-2", "What is 4 + (-6)?", "-2", ["2", "10", "-10"], "adding-integers", verify="4+(-6)", purpose="test"),
        item("q-add-3", "What is -7 + (-2)?", "-9", ["-5", "5", "9"], "adding-integers", difficulty="challenge", verify="-7+(-2)"),
        item("q-add-4", "What is 0 + (-3)?", "-3", ["3", "0", "-6"], "adding-integers", difficulty="intro"),
    ]
    (d / "lessons" / "line.yaml").write_text(yaml.safe_dump(lesson("line", "Moving on the line", "number-line", l1_items)), encoding="utf-8")
    (d / "lessons" / "adding.yaml").write_text(yaml.safe_dump(lesson("adding", "Adding integers", "adding-integers", l2_items)), encoding="utf-8")
    return root
