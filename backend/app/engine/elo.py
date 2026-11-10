"""Online Rasch (one-parameter IRT) ratings via Elo-style updates.

theta = learner ability per subject, beta = item difficulty. P(correct) = sigmoid(theta - beta).
Used to choose questions near the learner's level. A full IRT fit needs hundreds of responses per item, so this
learns online and can be replaced by an offline fit once real data exists.
"""
from __future__ import annotations

import math

BETA_PRIOR = {"intro": -1.0, "standard": 0.0, "challenge": 1.0}


def expected(theta: float, beta: float) -> float:
    return 1.0 / (1.0 + math.exp(-(theta - beta)))


def update(theta: float, beta: float, correct: bool, n_learner: int, n_item: int) -> tuple[float, float]:
    y = 1.0 if correct else 0.0
    e = expected(theta, beta)
    k_l = max(0.08, 0.5 / math.sqrt(1 + n_learner / 8))
    k_i = max(0.02, 0.15 / math.sqrt(1 + n_item / 20))
    return theta + k_l * (y - e), beta - k_i * (y - e)
