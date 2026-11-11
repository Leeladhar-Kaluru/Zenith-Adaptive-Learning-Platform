"""Predicted recall: how likely a student still remembers a topic, from how well it was known and how long ago it was last practised.

recall = p_known * exp(-days / stability). Stability (in days) grows with the number of observations and with the revision interval already earned,
so a well-practised topic fades slowly and a once-seen topic fades fast. This is a simple, explainable forgetting curve (not a fitted model); it is
used to say which topics are fading and to order revision, and every use shows its inputs.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

MODEL_VERSION = "retention-v1"
FADING_BELOW = 0.55


def stability_days(n_obs: int, interval_days: int = 0) -> float:
    return min(60.0, 2.0 + 1.2 * n_obs + 0.8 * interval_days)


def recall(p_known: float, n_obs: int, last_at: datetime | None, now: datetime | None = None, interval_days: int = 0) -> float:
    if last_at is None:
        return p_known
    now = now or datetime.now(timezone.utc)
    days = max(0.0, (now - last_at).total_seconds() / 86400)
    return p_known * math.exp(-days / stability_days(n_obs, interval_days))


def days_until(p_known: float, n_obs: int, last_at: datetime | None, threshold: float = FADING_BELOW, now: datetime | None = None, interval_days: int = 0) -> float | None:
    """Days from now until predicted recall falls to the threshold: None if it is already below, or never gets there."""
    if last_at is None or p_known <= threshold:
        return None
    now = now or datetime.now(timezone.utc)
    total = stability_days(n_obs, interval_days) * math.log(p_known / threshold)
    return max(0.0, total - max(0.0, (now - last_at).total_seconds() / 86400))
