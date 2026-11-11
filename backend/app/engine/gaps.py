"""Find where a student is lacking, and what to fix first.

Deterministic and auditable (no model decides anything):
- a gap needs real evidence (at least two answers) and a mastery estimate below 60 percent;
- the Wilson score interval says how wide the doubt still is for that many answers;
- the prerequisite graph traces a weak topic back to the earlier topic that is probably the real cause;
- priority = (1 - mastery) x (1 + half the number of later, not-yet-secure topics that build on it), with a share passed
  down to the root cause, so foundations rank above the topics they hold up.
"""
from __future__ import annotations

import math

from app.engine import graph

GAP_P = 0.60
MIN_N = 2
Z90 = 1.645


def wilson(correct: int, n: int, z: float = Z90) -> tuple[float, float]:
    """Wilson score interval for the share of questions answered right. With no answers, we know nothing: (0, 1)."""
    if n <= 0:
        return 0.0, 1.0
    p = correct / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _confidence(n: int) -> str:
    return "low" if n < 4 else "medium" if n < 8 else "high"


def rank_gaps(concepts: dict[str, dict], edges: list[tuple[str, str]], states: dict[str, dict]) -> dict:
    """concepts: id -> {title, grade}; edges: (prerequisite, concept); states: id -> {p, n, c, status}."""
    scope = set(concepts)
    edges = [(a, b) for a, b in edges if a in scope and b in scope]
    measured = {c: s for c, s in states.items() if c in scope and s["n"] > 0}
    weak = {c for c, s in measured.items() if s["n"] >= MIN_N and s["p"] < GAP_P and s["status"] != "secure"}
    secure = {c for c, s in measured.items() if s["status"] == "secure"}

    base, downstream, root_of = {}, {}, {}
    for c in weak:
        downstream[c] = len([d for d in graph.descendants(c, edges) if d in scope and d not in secure])
        base[c] = (1 - measured[c]["p"]) * (1 + 0.5 * downstream[c])
        root_of[c] = graph.investigate(c, edges, {k: v for k, v in measured.items()})["root"]
    boost = {c: 0.0 for c in weak}
    for c, r in root_of.items():
        if r and r in boost and r != c:
            boost[r] += 0.5 * base[c]

    out = []
    for c in weak:
        s = measured[c]
        lo, hi = wilson(s["c"], s["n"])
        r = root_of[c] if root_of[c] in scope else None
        reason = f"{s['c']} of {s['n']} answers right (your real level is probably between {round(lo * 100)}% and {round(hi * 100)}%)."
        if downstream[c]:
            reason += f" {downstream[c]} later topic{'s' if downstream[c] != 1 else ''} build on this."
        if r:
            reason += f" The real gap is earlier: {concepts[r]['title']}."
        out.append({"conceptId": c, "title": concepts[c]["title"], "grade": concepts[c]["grade"], "p": round(s["p"], 3), "n": s["n"], "correct": s["c"],
                    "interval": [round(lo, 3), round(hi, 3)], "band": "gap_confirmed" if s["p"] < 0.4 else "gap_suspected", "confidence": _confidence(s["n"]),
                    "priority": round(base[c] + boost[c], 3), "downstream": downstream[c], "root": {"id": r, "title": concepts[r]["title"]} if r else None, "reason": reason})
    out.sort(key=lambda g: (-g["priority"], -g["downstream"], g["conceptId"]))

    gap_ids = {g["conceptId"] for g in out}
    order = graph.topological_order(sorted(scope), edges)
    path = [c for c in order if c in gap_ids]
    unmeasured = [{"conceptId": c, "title": concepts[c]["title"], "grade": concepts[c]["grade"]} for c in sorted(scope - set(measured))]
    learning = len([c for c in measured if c not in secure and c not in gap_ids])
    return {"gaps": out, "repairPath": path, "unmeasured": unmeasured,
            "summary": {"secure": len(secure), "learning": learning, "gaps": len(out), "unmeasured": len(unmeasured)}}
