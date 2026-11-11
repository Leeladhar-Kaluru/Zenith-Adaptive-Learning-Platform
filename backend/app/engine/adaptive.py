"""Adaptive check: pick each next question by how much it tells us, and stop as soon as the estimate is precise enough.

Rasch model (the same one that drives learner and item ratings): P(correct) = sigmoid(theta - beta). The ability estimate is the MAP value with a
gentle normal prior around the learner's current rating, found by Newton steps. Its standard error comes from the Fisher information,
sum of p(1-p). A question is most informative when its difficulty is close to the current estimate. Pure functions: same inputs, same answer.
"""
from __future__ import annotations

import math
from typing import Sequence

MODEL_VERSION = "adaptive-rasch-v1"
MIN_ITEMS, MAX_ITEMS, TARGET_SE = 6, 12, 0.55


def p_correct(theta: float, beta: float) -> float:
    return 1.0 / (1.0 + math.exp(-(theta - beta)))


def estimate(responses: Sequence[tuple[float, bool]], prior_mean: float = 0.0, prior_sd: float = 1.0) -> tuple[float, float]:
    """(theta, standard error) from (item difficulty, was it right) pairs. With no responses it returns the prior and the prior's spread."""
    theta = prior_mean
    for _ in range(25):
        grad = sum((1.0 if ok else 0.0) - p_correct(theta, b) for b, ok in responses) - (theta - prior_mean) / prior_sd ** 2
        hess = sum(p_correct(theta, b) * (1 - p_correct(theta, b)) for b, _ in responses) + 1 / prior_sd ** 2
        step = grad / hess
        theta = max(-4.0, min(4.0, theta + step))
        if abs(step) < 1e-6:
            break
    info = sum(p_correct(theta, b) * (1 - p_correct(theta, b)) for b, _ in responses) + 1 / prior_sd ** 2
    return theta, 1.0 / math.sqrt(info)


def information(theta: float, beta: float) -> float:
    p = p_correct(theta, beta)
    return p * (1 - p)


def choose(cands: Sequence[dict], theta: float, seen_concepts: dict[str, int]) -> dict | None:
    """The most informative candidate. A topic not asked about yet gets a small bonus, so the check covers the scope instead of drilling one topic."""
    best, best_score = None, -1.0
    for c in cands:
        primary = max(c["concepts"], key=lambda cw: cw[1])[0]
        score = information(theta, c["beta"]) * (1.0 + 0.25 / (1 + seen_concepts.get(primary, 0)))
        if score > best_score or (score == best_score and best is not None and c["id"] < best["id"]):
            best, best_score = c, score
    return best


def should_stop(n: int, se: float, available: int) -> tuple[bool, str]:
    if n >= MAX_ITEMS:
        return True, f"Reached the most questions a check uses ({MAX_ITEMS})."
    if available == 0:
        return True, "No more suitable questions are available for this."
    if n >= MIN_ITEMS and se <= TARGET_SE:
        return True, f"The estimate is precise enough after {n} questions."
    return False, ""


def interval(theta: float, se: float) -> tuple[float, float]:
    """A 90 % interval, so the result is shown as a range and not a single number."""
    return theta - 1.645 * se, theta + 1.645 * se


def describe(theta: float) -> str:
    """Plain words for the ability scale, which centres on 0 for a typical standard question."""
    return "just starting" if theta < -1.2 else "building" if theta < -0.3 else "comfortable" if theta < 0.6 else "strong" if theta < 1.4 else "ready for challenge"
