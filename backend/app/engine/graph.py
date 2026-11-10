"""Concept prerequisite graph: validation, traversal and gap investigation."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable


class CycleError(ValueError):
    def __init__(self, nodes: list[str]):
        super().__init__(f"Prerequisite graph has a cycle involving: {', '.join(sorted(nodes)[:8])}")
        self.nodes = nodes


def topological_order(nodes: Iterable[str], edges: Iterable[tuple[str, str]]) -> list[str]:
    """Kahn's algorithm. Edges are (prereq, concept). Raises CycleError if not a DAG."""
    nodes = list(nodes)
    indeg = {n: 0 for n in nodes}
    out: dict[str, list[str]] = defaultdict(list)
    for a, b in edges:
        if a not in indeg or b not in indeg:
            raise ValueError(f"Edge references an unknown concept: {a} -> {b}")
        out[a].append(b)
        indeg[b] += 1
    q = deque(sorted(n for n, d in indeg.items() if d == 0))
    order: list[str] = []
    while q:
        n = q.popleft()
        order.append(n)
        for m in sorted(out[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    if len(order) != len(nodes):
        raise CycleError([n for n, d in indeg.items() if d > 0])
    return order


def ancestors(concept: str, edges: Iterable[tuple[str, str]], depth: int = 3) -> list[tuple[str, int]]:
    """Prerequisites of `concept` with their distance (1 = direct), nearest first."""
    parents: dict[str, list[str]] = defaultdict(list)
    for a, b in edges:
        parents[b].append(a)
    seen: dict[str, int] = {}
    frontier = [concept]
    for d in range(1, depth + 1):
        nxt: list[str] = []
        for c in frontier:
            for p in sorted(parents.get(c, [])):
                if p not in seen:
                    seen[p] = d
                    nxt.append(p)
        frontier = nxt
    return sorted(seen.items(), key=lambda kv: (kv[1], kv[0]))


def descendants(concept: str, edges: Iterable[tuple[str, str]]) -> set[str]:
    kids: dict[str, list[str]] = defaultdict(list)
    for a, b in edges:
        kids[a].append(b)
    out: set[str] = set()
    stack = [concept]
    while stack:
        for k in kids.get(stack.pop(), []):
            if k not in out:
                out.add(k)
                stack.append(k)
    return out


def investigate(target: str, edges: list[tuple[str, str]], state: dict[str, dict], depth: int = 3) -> dict:
    """Decide which prerequisites to probe and which gap is the root.

    `state[c]` = {"p": float, "n": int, "status": str}. Returns:
      {"probe": [concept ids that lack evidence, nearest first, max 2],
       "root": concept id of the deepest prerequisite that is weak while its own prerequisites are not, or None}
    A single wrong answer never confirms a gap.
    """
    anc = ancestors(target, edges, depth)
    probe: list[str] = []
    weak: list[tuple[str, int]] = []
    for c, d in anc:
        s = state.get(c)
        if s is None or s["n"] < 2:
            probe.append(c)
        elif s["p"] < 0.45:
            weak.append((c, d))
    root = None
    if weak:
        weak_ids = {c for c, _ in weak}
        # root = a weak prerequisite none of whose own prerequisites is weak (fix the foundation first)
        candidates = [c for c, d in weak if not any(a in weak_ids for a, _ in ancestors(c, edges, depth))]
        root = max(candidates, key=lambda c: dict(weak)[c]) if candidates else weak[-1][0]
    return {"probe": probe[:2], "root": root}
