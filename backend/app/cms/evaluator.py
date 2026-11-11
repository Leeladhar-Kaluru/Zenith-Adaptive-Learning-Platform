"""The evaluator: a scorecard for a machine-assisted lesson draft, computed without any model so every mark can be explained.

A draft that fails a hard check is rejected with the reason. One that passes is queued for a person; the scorecard travels with it so the reviewer
sees what was checked. Passing the evaluator never publishes anything."""
from __future__ import annotations

import re

from app.cms.draft import find_todos
from app.cms.gates import fk_grade

NGRAM = 8
MAX_OVERLAP = 0.15                       # share of the lesson's 8-word runs that also appear in the source: above this it is copying, not rewriting


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _prose(lesson: dict) -> str:
    parts: list[str] = []
    for b in lesson.get("blocks", []):
        if b.get("kind") in ("text", "callout"):
            parts.append(re.sub(r"<[^>]+>", " ", b.get("html", "")))
        elif b.get("kind") == "example":
            parts += [b.get("prompt", ""), *b.get("steps", [])]
        elif b.get("kind") == "summary":
            parts += b.get("points", [])
    return " ".join(parts)


def overlap(lesson_text: str, source_text: str) -> float:
    """Share of the lesson's n-word runs that also occur in the source."""
    mine, theirs = _words(lesson_text), _words(source_text)
    if len(mine) < NGRAM:
        return 0.0
    src = {tuple(theirs[i:i + NGRAM]) for i in range(len(theirs) - NGRAM + 1)}
    runs = [tuple(mine[i:i + NGRAM]) for i in range(len(mine) - NGRAM + 1)]
    return sum(r in src for r in runs) / len(runs)


def evaluate(lesson: dict, source_text: str, grade: int) -> dict:
    prose = _prose(lesson)
    items = lesson.get("items", [])
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str, hard: bool = False, weight: float = 1.0):
        checks.append({"name": name, "passed": bool(passed), "detail": detail, "hard": hard, "weight": weight})

    add("Labelled as machine-assisted and credited to its source", lesson.get("origin") == "ai_assisted" and bool(lesson.get("sources")),
        "origin is ai_assisted and a source asset is cited" if lesson.get("origin") == "ai_assisted" and lesson.get("sources") else "missing the ai_assisted label or the source credit", hard=True, weight=2)
    ov = overlap(prose, source_text)
    add("Rewritten, not copied", ov <= MAX_OVERLAP, f"{ov:.0%} of its 8-word runs appear in the source (limit {MAX_OVERLAP:.0%})", hard=True, weight=3)
    fk = fk_grade(prose)
    add("Reading level fits the class", fk <= grade + 2, f"reading grade {fk:.1f} for Class {grade} (limit {grade + 2})", weight=2)

    bad: list[str] = []
    stems: set[str] = set()
    letters: list[str] = []
    for it in items:
        opts = [o.get("text", "").strip().lower() for o in it.get("options", [])]
        keys = [o.get("key") for o in it.get("options", [])]
        stem = it.get("stem", "").strip().lower()
        if len(opts) != 4 or len(set(opts)) != 4 or it.get("correct") not in keys or not stem or stem in stems:
            bad.append(it.get("key", "?"))
        stems.add(stem)
        letters.append(it.get("correct"))
    add("Every question has four different options and one correct answer", not bad and len(items) > 0, "all questions are well formed" if not bad else f"problems in: {', '.join(bad[:5])}", hard=True, weight=3)
    add("Enough questions", len(items) >= 8, f"{len(items)} questions (need 8 or more)", weight=2)
    add("Correct answers are not all the same letter", len(set(letters)) >= 3 or len(items) < 8, f"answer letters used: {', '.join(sorted(set(filter(None, letters))))}", weight=1)
    levels = {it.get("difficulty") for it in items}
    add("Easy, standard and hard questions", {"intro", "standard", "challenge"} <= levels, f"levels present: {', '.join(sorted(l for l in levels if l))}", weight=1)

    examples = [b for b in lesson.get("blocks", []) if b.get("kind") == "example"]
    summary = next((b for b in lesson.get("blocks", []) if b.get("kind") == "summary"), {"points": []})
    add("Worked examples, objectives and a recap", len(examples) >= 2 and len(lesson.get("objectives", [])) >= 3 and len(summary.get("points", [])) >= 3,
        f"{len(examples)} examples, {len(lesson.get('objectives', []))} objectives, {len(summary.get('points', []))} recap points", weight=2)
    add("Wrong options are tied to named misconceptions", len(lesson.get("misconceptions", [])) >= 2, f"{len(lesson.get('misconceptions', []))} misconceptions tagged", weight=1)

    src_nums = set(re.findall(r"\d+(?:\.\d+)?", source_text))
    odd = sorted({n for n in re.findall(r"\d+(?:\.\d+)?", prose) if n not in src_nums})
    add("Numbers in the explanation come from the source", len(odd) <= 2, "all numbers appear in the source" if not odd else f"not found in the source: {', '.join(odd[:6])}", weight=1)

    todos = find_todos(lesson)
    add("Nothing left for a human to finish", not todos, "complete" if not todos else f"{len(todos)} item(s) still marked TODO (for example a diagram or hints)", weight=1)

    total = sum(c["weight"] for c in checks)
    score = round(sum(c["weight"] for c in checks if c["passed"]) / total, 3)
    failed_hard = [c["name"] for c in checks if c["hard"] and not c["passed"]]
    return {"checks": checks, "score": score, "verdict": "rejected" if failed_hard else "review", "rejectedBecause": failed_hard, "todos": len(todos)}
