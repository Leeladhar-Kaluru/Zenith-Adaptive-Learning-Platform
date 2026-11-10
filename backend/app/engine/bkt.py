"""Bayesian Knowledge Tracing with item-aware guess and slip, plus honest status bands.

Parameters are expert priors (`PARAM_VERSION = "prior-v1"`), not fitted values. Every evidence row records the
version used so a later fit on real data can be compared against the priors.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

PARAM_VERSION = "prior-v1"
P_INIT = 0.25
P_TRANSIT = 0.15
SLIP = {"intro": 0.06, "standard": 0.10, "challenge": 0.15}
ASSISTED_GUESS = 0.60       # a correct answer after hints is weak evidence of knowing
MIN_OBS_FOR_BAND = 3
SECURE_P, SECURE_N = 0.85, 4
GAP_P = 0.40


def guess_prob(kind: str, n_options: int = 4) -> float:
    """Chance of a correct answer without knowing the concept, from the response format."""
    if kind == "mcq":
        return min(0.5, max(0.15, 1.0 / max(2, n_options)))
    return {"truefalse": 0.5, "multi": 0.08, "numeric": 0.04, "fill": 0.06, "match": 0.10}.get(kind, 0.25)


def posterior(p: float, correct: bool, guess: float, slip: float, transit: float = P_TRANSIT) -> float:
    """One BKT step: Bayes update on the observation, then the chance of learning during the attempt."""
    p = min(0.999, max(0.001, p))
    if correct:
        num = p * (1 - slip)
        den = num + (1 - p) * guess
    else:
        num = p * slip
        den = num + (1 - p) * (1 - guess)
    post = num / den
    return min(0.999, max(0.001, post + (1 - post) * transit))


def update(p: float, *, correct: bool, kind: str, n_options: int, difficulty: str, hints_used: int, weight: float = 1.0) -> float:
    guess = ASSISTED_GUESS if (correct and hints_used > 0) else guess_prob(kind, n_options)
    new = posterior(p, correct, guess, SLIP.get(difficulty, 0.10))
    w = min(1.0, max(0.0, weight))
    return min(0.999, max(0.001, p + w * (new - p)))


@dataclass(frozen=True)
class Summary:
    p_known: float
    n_obs: int
    n_correct: int


def status(p: float, n_obs: int, n_correct: int) -> str:
    """Band shown to students and teachers. Needs real evidence before saying anything strong."""
    if n_obs < MIN_OBS_FOR_BAND:
        return "gap_suspected" if (n_obs >= 2 and n_correct == 0) else "unassessed"
    if p >= SECURE_P and n_obs >= SECURE_N:
        return "secure"
    if p < GAP_P:
        return "gap_confirmed" if (n_obs >= 4 and n_correct / n_obs < 0.4) else "gap_suspected"
    return "learning"


def level(p: float, n_obs: int) -> int:
    """Practice level 1-3 for a concept. Rises only with evidence, never with time spent."""
    if n_obs < MIN_OBS_FOR_BAND or p < 0.45:
        return 1
    return 3 if p >= 0.75 else 2


def uncertainty(n_obs: int) -> str:
    """Plain-language confidence. We report how much evidence there is, not a fake interval."""
    return "low" if n_obs < 3 else "medium" if n_obs < 8 else "high"
