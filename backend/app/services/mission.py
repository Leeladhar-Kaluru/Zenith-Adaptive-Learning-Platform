"""The daily mission: at most three short steps (revise, learn, stretch) chosen from the student's real evidence, with the reason for each."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.engine import policy
from app.models import Profile
from app.services import home

MAX_MINUTES = 12
SLOT_MINUTES = {"revision": 4, "new": 5, "challenge": 3}      # a share of the 12 minutes for each part, so none is squeezed out
SLOTS = ("revision", "new", "challenge")
NEW_RULES = ("assigned_due", "assigned", "prereq", "continue", "practice", "next_lesson")


def _item(slot: str, step: dict, minutes: int) -> dict:
    return {"slot": slot, "title": step["title"], "reason": step["reason"], "minutes": minutes, "evidenceCount": step["evidenceCount"], "href": step["href"], "kind": step["kind"]}


def mission(db: Session, profile: Profile, steps: list[dict] | None = None) -> dict:
    steps = steps if steps is not None else home.next_steps(db, profile)
    probe = next((s for s in steps if s["rule"] == "probe"), None)
    if probe:
        return {"items": [], "totalMinutes": 0, "reason": "Start with a quick check so ZENITH can see where you are. It is not a graded test.", "href": probe["href"]}
    chosen: dict[str, dict] = {}
    review = next((s for s in steps if s["rule"] == "review"), None)
    if review:
        chosen["revision"] = review
    new = [s for s in steps if s["rule"] in NEW_RULES]
    if new:
        chosen["new"] = max(new, key=lambda s: policy.PRIORITY[s["rule"]])
    stretch = next((s for s in steps if s["rule"] == "challenge"), None)
    if stretch:
        chosen["challenge"] = stretch
    items, used = [], 0
    for slot in SLOTS:
        if slot not in chosen:
            continue
        minutes = max(1, min(int(chosen[slot]["minutes"]), SLOT_MINUTES[slot], MAX_MINUTES - used))
        items.append(_item(slot, chosen[slot], minutes))
        used += minutes
    return {"items": items, "totalMinutes": used, "reason": "" if items else "You are all caught up. Pick any topic to practise.", "href": "/learn" if not items else ""}
