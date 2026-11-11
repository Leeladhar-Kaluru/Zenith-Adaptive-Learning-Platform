"""Reading-level maths with no heavy imports, so the serverless API can use it (gates.py needs SymPy, which production does not install)."""
from __future__ import annotations

import re


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
