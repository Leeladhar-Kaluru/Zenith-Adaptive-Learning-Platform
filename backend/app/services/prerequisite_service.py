"""Prerequisite DAG Gap Traversal Service for SETU.

Navigates curriculum dependency graphs backward to isolate root foundation gaps.
Backward DAG BFS up to depth 3 isolates root unmastered foundation bridge concepts (grade < 10).
Pure deterministic graph algorithms with zero LLM dependencies (Requirement 11).
"""
from __future__ import annotations

import json
import os
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.models.library import Concept, ConceptEdge
from app.models.mastery import BktState

LIBRARY_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "content",
    "library",
)
MANIFEST_PATH = os.path.join(LIBRARY_BASE_DIR, "cbse-10-math", "manifest.json")


@dataclass
class GapConcept:
    concept_id: str
    title: str
    grade: int
    depth: int
    path: List[str]
    p_know: float
    is_gap: bool
    is_foundation: bool
    priority_score: float

    def to_dict(self) -> Dict[str, any]:
        return {
            "concept_id": self.concept_id,
            "title": self.title,
            "grade": self.grade,
            "depth": self.depth,
            "path": self.path,
            "p_know": self.p_know,
            "is_gap": self.is_gap,
            "is_foundation": self.is_foundation,
            "priority_score": self.priority_score,
        }


@dataclass
class PrerequisiteGapReport:
    has_gaps: bool
    root_gap: Optional[GapConcept] = None
    all_gaps: List[GapConcept] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, any]:
        return {
            "has_gaps": self.has_gaps,
            "root_gap": self.root_gap.to_dict() if self.root_gap else None,
            "all_gaps": [g.to_dict() for g in self.all_gaps],
            "explanation": self.explanation,
        }


def _load_manifest_dag_fallback() -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, any]]]:
    """Fallback loader for DAG edges and concept metadata across all manifest.json files."""
    reverse_adj: Dict[str, List[str]] = {}
    concept_meta: Dict[str, Dict[str, any]] = {}

    manifest_files = []
    if os.path.exists(LIBRARY_BASE_DIR):
        for entry in os.listdir(LIBRARY_BASE_DIR):
            cand = os.path.join(LIBRARY_BASE_DIR, entry, "manifest.json")
            if os.path.isfile(cand):
                manifest_files.append(cand)
    if not manifest_files and os.path.exists(MANIFEST_PATH):
        manifest_files.append(MANIFEST_PATH)

    for m_path in manifest_files:
        try:
            with open(m_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            m_grade = data.get("grade", 10)
            for ch in data.get("chapters", []):
                for c in ch.get("concepts", []):
                    concept_meta[c["id"]] = {
                        "title": c.get("title", c["id"]),
                        "grade": c.get("grade", m_grade),
                        "slug": c.get("slug", ""),
                    }

            for edge in data.get("dagEdges", []):
                parent = edge.get("fromConceptId")
                child = edge.get("toConceptId")
                if parent and child:
                    reverse_adj.setdefault(child, []).append(parent)
        except Exception:
            pass

    return reverse_adj, concept_meta


def get_incoming_prerequisites(db: Optional[Session], concept_id: str) -> List[str]:
    """Fetches immediate predecessor (prerequisite) concept IDs for a target concept.
    
    Database first, falling back to manifest.json if no DB records exist.
    """
    if db is not None:
        try:
            edges = (
                db.query(ConceptEdge)
                .filter(ConceptEdge.to_concept_id == concept_id)
                .all()
            )
            if edges:
                return [e.from_concept_id for e in edges]
        except Exception:
            pass

    # Fallback to manifest.json
    reverse_adj, _ = _load_manifest_dag_fallback()
    return reverse_adj.get(concept_id, [])


def find_root_prerequisite_gap(
    db: Optional[Session],
    student_id: uuid.UUID,
    concept_id: str,
    max_depth: int = 3,
) -> PrerequisiteGapReport:
    """Backward DAG BFS up to depth 3 to isolate root unmastered foundation bridge concepts.
    
    1. Traverses prerequisite edges backwards (child -> parents).
    2. Gathers student BKT states for discovered ancestor concepts.
    3. Identifies unmastered concepts (is_gap == True, p_know < 0.60, or 0 opportunities).
    4. Prioritizes foundation bridge concepts (grade < 10) at greater depths.
    5. Returns structured PrerequisiteGapReport with explanation.
    """
    queue = deque([(concept_id, 0, [concept_id])])
    visited: Set[str] = {concept_id}
    ancestor_nodes: List[Tuple[str, int, List[str]]] = []  # (concept_id, depth, path)

    # BFS backwards through incoming prerequisite edges
    while queue:
        curr, depth, path = queue.popleft()
        if depth >= max_depth:
            continue

        parents = get_incoming_prerequisites(db, curr)
        for p in parents:
            if p not in visited:
                visited.add(p)
                p_depth = depth + 1
                p_path = path + [p]
                ancestor_nodes.append((p, p_depth, p_path))
                queue.append((p, p_depth, p_path))

    if not ancestor_nodes:
        return PrerequisiteGapReport(
            has_gaps=False,
            root_gap=None,
            all_gaps=[],
            explanation="No prerequisite concepts found for this topic.",
        )

    ancestor_ids = [a[0] for a in ancestor_nodes]

    # Fetch BKT states from DB if available
    bkt_states: Dict[str, BktState] = {}
    concept_meta: Dict[str, Concept] = {}

    if db is not None:
        try:
            states = (
                db.query(BktState)
                .filter(
                    BktState.student_id == student_id,
                    BktState.concept_id.in_(ancestor_ids),
                )
                .all()
            )
            bkt_states = {s.concept_id: s for s in states}

            concepts = (
                db.query(Concept)
                .filter(Concept.id.in_(ancestor_ids))
                .all()
            )
            concept_meta = {c.id: c for c in concepts}
        except Exception:
            pass

    # Supplement missing concept metadata from manifest fallback
    _, manifest_meta = _load_manifest_dag_fallback()

    # Identify unmastered ancestors
    unmastered: List[GapConcept] = []
    for a_id, depth, path in ancestor_nodes:
        state = bkt_states.get(a_id)
        p_know = state.p_know if state else 0.25
        is_gap = state.is_gap if state else False
        total_ops = state.total_opportunities if state else 0

        c_model = concept_meta.get(a_id)
        m_info = manifest_meta.get(a_id, {})
        title = c_model.title if c_model else m_info.get("title", a_id)
        grade = c_model.grade if c_model else m_info.get("grade", 10)
        is_foundation = grade < 10

        # Struggle criteria: confirmed gap, low p_know (< 0.60), or zero attempts
        if is_gap or p_know < 0.60 or total_ops == 0:
            priority_score = (
                (100.0 if is_gap else 0.0)
                + (50.0 if is_foundation else 0.0)
                + (depth * 20.0)
                - (p_know * 50.0)
            )
            unmastered.append(
                GapConcept(
                    concept_id=a_id,
                    title=title,
                    grade=grade,
                    depth=depth,
                    path=path,
                    p_know=p_know,
                    is_gap=is_gap,
                    is_foundation=is_foundation,
                    priority_score=priority_score,
                )
            )

    if not unmastered:
        return PrerequisiteGapReport(
            has_gaps=False,
            root_gap=None,
            all_gaps=[],
            explanation="All prerequisite concepts are adequately mastered.",
        )

    # Rank by priority score descending
    unmastered.sort(key=lambda x: x.priority_score, reverse=True)
    root = unmastered[0]

    explanation = (
        f"Struggle in '{concept_id}' traces back {root.depth} level{'s' if root.depth > 1 else ''} "
        f"to foundation concept '{root.title}' (Grade {root.grade})."
    )

    return PrerequisiteGapReport(
        has_gaps=True,
        root_gap=root,
        all_gaps=unmastered,
        explanation=explanation,
    )
