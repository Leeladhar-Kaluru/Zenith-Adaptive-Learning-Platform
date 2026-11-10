"""Choose the next practice item: close to the learner's level, aimed at the concepts that need work."""
from __future__ import annotations

import random
from typing import Optional, Sequence

from app.engine import bkt, elo

TARGETS = {"practice": 0.75, "challenge": 0.60, "repair": 0.85, "test": 0.65}


def choose_item(cands: Sequence[dict], theta: float, states: dict[str, dict], recent_ids: set[str],
                mode: str = "practice", rng: Optional[random.Random] = None) -> Optional[dict]:
    """cands: [{id, difficulty, beta, concepts: [(concept_id, weight)]}], states: {concept: {p, n}}."""
    rng = rng or random.Random()
    target = TARGETS.get(mode, 0.75)

    def p_of(c: str) -> float:
        return states.get(c, {}).get("p", bkt.P_INIT)

    def eligible(it: dict, relax: bool) -> bool:
        ps = [p_of(c) for c, _ in it["concepts"]] or [bkt.P_INIT]
        if not relax:
            if it["id"] in recent_ids:
                return False
            if it["difficulty"] == "challenge" and mode != "challenge" and max(ps) < 0.60:
                return False          # harder questions unlock with evidence
            if it["difficulty"] == "intro" and min(ps) >= 0.80:
                return False          # no trivial questions once a concept is secure
        return True

    pool = [c for c in cands if eligible(c, False)] or [c for c in cands if eligible(c, True)]
    if not pool:
        return None

    def score(it: dict) -> float:
        need = sum(w * (1 - p_of(c)) for c, w in it["concepts"]) / max(1e-9, sum(w for _, w in it["concepts"]) or 1)
        gap = abs(elo.expected(theta, it["beta"]) - target)
        return gap - 0.25 * need + rng.random() * 0.02

    return min(pool, key=score)
