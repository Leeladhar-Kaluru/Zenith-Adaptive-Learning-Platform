"""Streak and level rules. Pure functions over real activity dates and XP totals."""
from __future__ import annotations

import math
from datetime import date, timedelta


def streak(active_days: set[date], today: date) -> dict:
    """Consecutive learning days. One missed day per rolling 7 days is forgiven (a free rest day).

    Today counts if active; if not yet active, the streak is still alive from yesterday until today ends.
    """
    days = 0
    d = today if today in active_days else today - timedelta(days=1)
    rests: list[date] = []
    while True:
        if d in active_days:
            days += 1
            d -= timedelta(days=1)
            continue
        recent_rest = any((r - d).days < 7 for r in rests)
        if not recent_rest and (d - timedelta(days=1)) in active_days:
            rests.append(d)
            d -= timedelta(days=1)
            continue
        break
    rest_available = not any((today - r).days < 7 for r in rests)
    return {"days": days, "restDayAvailable": rest_available, "activeToday": today in active_days}


def level(xp: int) -> dict:
    """Level n starts at 50*(n-1)^2 XP, so early levels come quickly and later ones take real learning."""
    lv = int(math.sqrt(max(0, xp) / 50)) + 1
    lo, hi = 50 * (lv - 1) ** 2, 50 * lv ** 2
    return {"level": lv, "xp": xp, "intoLevel": xp - lo, "forNext": hi - lo, "progress": round(100 * (xp - lo) / (hi - lo))}


def max_correct_run(flags: list[bool]) -> int:
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best
