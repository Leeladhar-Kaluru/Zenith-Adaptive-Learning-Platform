"""Turn raw interaction events for one question into plain signals the ladder can use."""
from __future__ import annotations

GUESS_FRACTION = 0.15      # answered in under 15 percent of the usual time
FLUENT_FRACTION = 0.70     # answered in under 70 percent of the usual time


def classify(events: list[dict], ms: int, correct: bool, median_ms: float) -> dict:
    """events: interaction events for this item, each {"kind": ..}. ms: time to answer. median_ms: typical time for the concept."""
    hints = sum(1 for e in events if e["kind"] == "hint_open")
    changes = sum(1 for e in events if e["kind"] == "answer_change")
    skips = sum(1 for e in events if e["kind"] == "skip")
    fast = median_ms > 0 and ms < GUESS_FRACTION * median_ms
    guessing = fast and not correct
    quick = median_ms > 0 and ms < FLUENT_FRACTION * median_ms
    fluent = correct and hints == 0 and quick and not fast
    struggling = hints >= 2 or changes >= 2 or skips >= 1
    if guessing:
        why = "Answered very fast and got it wrong, which looks like guessing."
    elif fluent:
        why = "Correct without help and faster than usual."
    elif struggling:
        why = "Used several hints or changed the answer several times."
    else:
        why = "Normal pace."
    return {"fluent": fluent, "struggling": struggling, "guessing": guessing, "reason": why}
