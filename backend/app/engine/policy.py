"""Next-best-action: transparent rules over real evidence. Every suggestion carries its reason and evidence count."""
from __future__ import annotations

from typing import Optional

MODEL_VERSION = "rules-v1"

PRIORITY = {"assigned_due": 90, "prereq": 80, "probe": 70, "review": 60, "continue": 50, "assigned": 45,
            "practice": 40, "next_lesson": 30, "challenge": 20}


def pick(candidates: list[dict]) -> Optional[dict]:
    """Highest priority wins; ties keep the order given (most recent evidence first)."""
    if not candidates:
        return None
    best = max(range(len(candidates)), key=lambda i: (PRIORITY[candidates[i]["rule"]], -i))
    return candidates[best]


def step(rule: str, kind: str, title: str, reason: str, href: str, minutes: int, evidence: int = 0, **extra) -> dict:
    return {"rule": rule, "kind": kind, "title": title, "reason": reason, "href": href, "minutes": minutes,
            "evidenceCount": evidence, **extra}
