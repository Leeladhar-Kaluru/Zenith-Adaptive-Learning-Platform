"""Automated review gates. They surface problems for a human reviewer; they never approve anything."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

import sympy
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application

from app.engine.grading import parse_number

_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


@dataclass
class Gate:
    name: str
    passed: bool
    detail: str = ""
    manual: bool = False


def _strip_html(h: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups) - (1 if w.endswith("e") and len(groups) > 1 else 0)
    return max(1, n)


def fk_grade(text: str) -> float:
    """Flesch-Kincaid grade level (English). Rough but consistent; used as a guard against overly dense text."""
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"[A-Za-z']+", text)
    if not sentences or not words:
        return 0.0
    syl = sum(_syllables(w) for w in words)
    return 0.39 * (len(words) / len(sentences)) + 11.8 * (syl / len(words)) - 15.59


def sympy_value(expr: str) -> sympy.Expr:
    return sympy.nsimplify(parse_expr(expr.replace("^", "**").replace("−", "-"), transformations=_TRANSFORMS, evaluate=True))


def lesson_gates(*, title: str, grade: int, objectives: list[str], blocks: list[dict], items: list[dict], concept_ids: set[str],
                 known_concepts: set[str], graph_error: str | None, curriculum_verified: bool, misconception_codes: set[str]) -> list[Gate]:
    g: list[Gate] = []
    checks = [b for b in blocks if b["kind"] == "check"]
    g.append(Gate("Structure is complete", bool(objectives) and len(blocks) >= 3 and bool(checks),
                  f"{len(objectives)} objectives, {len(blocks)} blocks, {len(checks)} understanding checks"))

    # one correct answer, distinct options
    bad = []
    for it in items:
        if it["kind"] in ("mcq", "multi"):
            texts = [o["text"].strip().lower() for o in it["options"]]
            if len(set(texts)) != len(texts) or any(not t for t in texts):
                bad.append(it["key"])
    g.append(Gate("Options are distinct", not bad, ("Duplicate or empty options in: " + ", ".join(bad)) if bad else f"{len(items)} items checked"))

    # SymPy verification
    verified, failed, unverifiable = 0, [], 0
    for it in items:
        expr = it.get("verify")
        if not expr:
            unverifiable += 1
            continue
        try:
            want = sympy_value(expr)
            if it["kind"] == "numeric":
                given = parse_number(it["value"])
                ok = given is not None and sympy.simplify(want - sympy.Rational(given.numerator, given.denominator)) == 0
            elif it["kind"] == "mcq":
                opts = {o["key"]: parse_number(o["text"]) for o in it["options"]}
                right = opts.get(it["correct"])
                ok = right is not None and sympy.simplify(want - sympy.Rational(right.numerator, right.denominator)) == 0
                # no distractor may also equal the answer
                ok = ok and not any(k != it["correct"] and v is not None and sympy.simplify(want - sympy.Rational(v.numerator, v.denominator)) == 0 for k, v in opts.items())
            else:
                ok = False
        except Exception as exc:  # noqa: BLE001
            ok = False
            failed.append(f"{it['key']} ({type(exc).__name__})")
            continue
        if ok:
            verified += 1
        else:
            failed.append(it["key"])
    g.append(Gate("Answers verified with SymPy", not failed,
                  ("Does not check out: " + ", ".join(failed)) if failed else f"{verified} verified, {unverifiable} not machine-verifiable (reviewer reads those)"))

    # readability
    prose = " ".join(_strip_html(b.get("html", "")) for b in blocks if b["kind"] in ("text", "callout"))
    fk = fk_grade(prose)
    limit = grade + 2
    g.append(Gate(f"Readable for Class {grade}", fk <= limit, f"Reading level about grade {fk:.1f} (limit {limit})"))

    # maths notation
    tex_bad = []
    for b in blocks:
        for m in re.finditer(r'data-tex="([^"]*)"', b.get("html", "")):
            t = m.group(1)
            if t.count("{") != t.count("}") or t.count("\\left") != t.count("\\right"):
                tex_bad.append(t[:30])
    g.append(Gate("Maths notation is well-formed", not tex_bad, ("Unbalanced: " + "; ".join(tex_bad)) if tex_bad else "ok"))

    figs = [b for b in blocks if b["kind"] == "figure"]
    missing_alt = [b for b in figs if len(b.get("alt", "").strip()) < 8]
    g.append(Gate("Figures have alt text", not missing_alt, f"{len(figs)} figure{'' if len(figs) == 1 else 's'}"))

    unknown = {c["id"] for it in items for c in it["concepts"]} - known_concepts
    g.append(Gate("Questions are mapped to known concepts", not unknown, ("Unknown: " + ", ".join(sorted(unknown))) if unknown else f"{len(concept_ids)} lesson concepts"))

    tagged = sum(1 for it in items if it["kind"] == "mcq" for o in it["options"] if o.get("misconception"))
    undefined = {o["misconception"] for it in items for o in it.get("options", []) if o.get("misconception")} - misconception_codes
    g.append(Gate("Common mistakes are tagged", tagged >= 1 and not undefined,
                  ("Undefined misconception codes: " + ", ".join(sorted(undefined))) if undefined else f"{tagged} wrong options map to a known mistake"))

    practice = [it for it in items if it["purpose"] in ("practice", "test", "probe")]
    g.append(Gate("Enough practice questions", len(items) >= 4 and len(practice) >= 2, f"{len(items)} questions ({len(practice)} for practice or tests)"))

    g.append(Gate("Prerequisite graph is acyclic", graph_error is None, graph_error or "ok"))
    g.append(Gate("Curriculum mapping confirmed", curriculum_verified, "Chapter placement checked against the board's current textbook" if curriculum_verified else "Reviewer must confirm the chapter matches the current textbook", manual=True))
    return g
