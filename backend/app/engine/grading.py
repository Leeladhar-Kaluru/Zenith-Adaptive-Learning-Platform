"""Deterministic answer checking. No LLM is ever involved in deciding whether an answer is correct."""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

_MINUS = str.maketrans({"−": "-", "–": "-", "—": "-"})


@dataclass(frozen=True)
class Grade:
    correct: bool
    score: float            # 0..1, partial credit for multi and match
    reveal: Any             # what is shown to the student after answering
    selected: Any = None    # normalised response (used to look up a misconception)


def parse_number(text: Any) -> Fraction | None:
    """Parse 3, -3, −3, 0.5, 3/4, -3/4 and thousands separators. Returns None if not a number."""
    if isinstance(text, bool):
        return None
    if isinstance(text, (int, float)):
        return Fraction(str(text))
    s = str(text).translate(_MINUS).strip().replace(",", "").replace(" ", "")
    if not s:
        return None
    try:
        if "/" in s:
            a, b = s.split("/", 1)
            if not b or Fraction(b) == 0:
                return None
            return Fraction(a) / Fraction(b)
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        return None


def _norm_text(s: Any, case: bool) -> str:
    t = re.sub(r"\s+", " ", str(s).translate(_MINUS)).strip()
    return t if case else t.lower()


def grade(kind: str, spec: dict, response: dict) -> Grade:
    if kind == "mcq":
        choice = str(response.get("choice", "")).strip().upper()
        ok = choice == str(spec["correct"]).upper()
        return Grade(ok, 1.0 if ok else 0.0, spec["correct"], choice)

    if kind == "truefalse":
        raw = response.get("choice")
        choice = raw if isinstance(raw, bool) else str(raw).strip().lower() in ("true", "t", "yes")
        ok = choice == bool(spec["correct"])
        return Grade(ok, 1.0 if ok else 0.0, bool(spec["correct"]), choice)

    if kind == "multi":
        want = {str(x).upper() for x in spec["correct"]}
        got = {str(x).upper() for x in response.get("choices", [])}
        ok = got == want
        score = max(0.0, (len(got & want) - len(got - want)) / max(1, len(want)))
        return Grade(ok, 1.0 if ok else round(min(score, 0.99), 3), sorted(want), sorted(got))

    if kind == "numeric":
        got = parse_number(response.get("value"))
        want = parse_number(spec["value"])
        tol = Fraction(str(spec.get("tolerance", 0)))
        ok = got is not None and want is not None and abs(got - want) <= tol
        return Grade(ok, 1.0 if ok else 0.0, spec["value"], None if got is None else float(got))

    if kind == "fill":
        case = bool(spec.get("case", False))
        got = _norm_text(response.get("text", ""), case)
        accepted = {_norm_text(a, case) for a in spec["accepted"]}
        ok = got in accepted
        return Grade(ok, 1.0 if ok else 0.0, spec["accepted"][0], got)

    if kind == "match":
        want: dict = spec["pairs"]
        got = response.get("pairs", {}) or {}
        right = sum(1 for k, v in want.items() if got.get(k) == v)
        ok = right == len(want) and len(got) == len(want)
        return Grade(ok, round(right / max(1, len(want)), 3) if not ok else 1.0, want, got)

    raise ValueError(f"Unsupported item kind: {kind}")


def public_payload(kind: str, payload: dict) -> dict:
    """Strip anything that could leak the answer before an item is sent to a student."""
    p = dict(payload)
    p.pop("correct", None)
    if kind == "match":
        # shuffle-safe: send the left items in order and the right items sorted so position does not reveal the pairing
        p["right"] = sorted(p.get("right", []))
    return p
