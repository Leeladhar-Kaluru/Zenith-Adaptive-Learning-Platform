"""Difficulty ladder (levels 1-5) per concept. Deterministic and explainable: every move returns its reason."""
from __future__ import annotations

MIN_LEVEL, MAX_LEVEL = 1, 5
UP_AFTER, DOWN_AFTER = 2, 2


def step(level: int, streak_up: int, streak_down: int, *, correct: bool, hints_used: int = 0,
         fluent: bool = False, struggling: bool = False, guessing: bool = False) -> tuple[int, int, int, str]:
    """Return (new_level, streak_up, streak_down, reason).

    Up: two clean (no hint) correct answers in a row, or one if the answer was fluent. Guessing never raises the level.
    Down: two wrong answers in a row, or one if the student was visibly struggling. A hinted correct answer is neutral.
    """
    level = max(MIN_LEVEL, min(MAX_LEVEL, level))
    if correct and hints_used > 0:
        return level, streak_up, 0, "Correct with a hint, so the level stays and the streak is kept."
    if correct:
        if guessing:
            return level, 0, 0, "Answered too quickly to tell if it was understood, so the level stays."
        up = streak_up + 1
        if (up >= UP_AFTER or fluent) and level < MAX_LEVEL:
            why = "Correct quickly and confidently" if fluent and up < UP_AFTER else f"{up} correct answers in a row without hints"
            return level + 1, 0, 0, f"{why}, so questions get harder."
        return level, up, 0, "Correct. One more clean answer moves you up." if level < MAX_LEVEL else "Correct at the top level."
    down = streak_down + 1
    if (down >= DOWN_AFTER or struggling) and level > MIN_LEVEL:
        why = "Several hints and changes before answering" if struggling and down < DOWN_AFTER else f"{down} wrong answers in a row"
        return level - 1, 0, 0, f"{why}, so questions get a little easier to rebuild the basics."
    return level, 0, down, "Not quite. The level stays; review the explanation and try another."
