"""Adversarial stress-testing suite for Prerequisite DAG Gap Traversal.

Empirical verification of:
1. Deep 10-node & 100-node prerequisite chains with strict max_depth cutoff.
2. Circular prerequisite graphs (3-cycle, self-loop, figure-eight, entangled cycles) defensive handling.
3. Disconnected graphs & fully-mastered ancestor graphs returning has_gaps=False.
4. Consistent prioritization of foundation bridge concepts (grade < 10) over grade 10 concepts.
5. Error recovery: DB exceptions, non-existent concepts, manifest fallbacks.
"""
from __future__ import annotations

import uuid
from typing import List
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "TEXT"

from app.models.base import Base
from app.models.library import Concept, ConceptEdge
from app.models.mastery import BktState
from app.services.prerequisite_service import (
    find_root_prerequisite_gap,
    get_incoming_prerequisites,
    PrerequisiteGapReport,
)


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def test_student_id():
    return uuid.uuid4()


class TestPrerequisiteChainDepthCutoff:
    """Stress tests verifying traversal depth bounds on long linear chains."""

    def test_10_node_linear_chain_depth_cutoff_at_max_depth_3(self, memory_db, test_student_id):
        """Chain: N1 -> N2 -> ... -> N10. Querying N10 at max_depth=3 must return only N9, N8, N7."""
        # N1 is prereq for N2, ..., N9 is prereq for N10
        for i in range(1, 11):
            c = Concept(id=f"chain-node-{i}", slug=f"slug-{i}", title=f"Node {i}", grade=i, p_l0=0.25)
            memory_db.add(c)
        memory_db.flush()

        for i in range(1, 10):
            edge = ConceptEdge(from_concept_id=f"chain-node-{i}", to_concept_id=f"chain-node-{i+1}")
            memory_db.add(edge)
        memory_db.flush()

        # Query Node 10 with max_depth=3
        report = find_root_prerequisite_gap(memory_db, test_student_id, "chain-node-10", max_depth=3)

        assert report.has_gaps is True
        gap_ids = [g.concept_id for g in report.all_gaps]
        gap_depths = {g.concept_id: g.depth for g in report.all_gaps}

        # Must strictly contain depths 1, 2, 3
        assert set(gap_ids) == {"chain-node-9", "chain-node-8", "chain-node-7"}
        assert gap_depths["chain-node-9"] == 1
        assert gap_depths["chain-node-8"] == 2
        assert gap_depths["chain-node-7"] == 3

        # Must NOT contain depth >= 4
        for forbidden_idx in range(1, 7):
            assert f"chain-node-{forbidden_idx}" not in gap_ids

    def test_depth_cutoff_boundary_values(self, memory_db, test_student_id):
        """Tests max_depth=1 (immediate parents only) and max_depth=0 (empty)."""
        c1 = Concept(id="bound-n1", slug="b1", title="B1", grade=9, p_l0=0.25)
        c2 = Concept(id="bound-n2", slug="b2", title="B2", grade=10, p_l0=0.25)
        memory_db.add_all([c1, c2])
        memory_db.add(ConceptEdge(from_concept_id="bound-n1", to_concept_id="bound-n2"))
        memory_db.flush()

        # max_depth=1
        report_d1 = find_root_prerequisite_gap(memory_db, test_student_id, "bound-n2", max_depth=1)
        assert report_d1.has_gaps is True
        assert len(report_d1.all_gaps) == 1
        assert report_d1.all_gaps[0].concept_id == "bound-n1"

        # max_depth=0
        report_d0 = find_root_prerequisite_gap(memory_db, test_student_id, "bound-n2", max_depth=0)
        assert report_d0.has_gaps is False
        assert len(report_d0.all_gaps) == 0

    def test_100_node_chain_performance_and_no_recursion_limit(self, memory_db, test_student_id):
        """A 100-node chain must not trigger RecursionError or slow performance."""
        for i in range(1, 101):
            memory_db.add(Concept(id=f"deep-{i}", slug=f"d-{i}", title=f"Deep {i}", grade=10, p_l0=0.25))
        memory_db.flush()

        for i in range(1, 100):
            memory_db.add(ConceptEdge(from_concept_id=f"deep-{i}", to_concept_id=f"deep-{i+1}"))
        memory_db.flush()

        report = find_root_prerequisite_gap(memory_db, test_student_id, "deep-100", max_depth=3)
        assert report.has_gaps is True
        assert len(report.all_gaps) == 3
        assert {g.concept_id for g in report.all_gaps} == {"deep-99", "deep-98", "deep-97"}


class TestPrerequisiteCyclicGraphSafety:
    """Stress tests verifying defensive cycle handling in circular prerequisite networks."""

    def test_3_node_directed_cycle_terminates_defensively(self, memory_db, test_student_id):
        """Cycle: A -> B -> C -> A. Backward traversal from A visits C, then B, and stops cleanly."""
        ca = Concept(id="cyc-a", slug="ca", title="Cycle A", grade=10, p_l0=0.25)
        cb = Concept(id="cyc-b", slug="cb", title="Cycle B", grade=9, p_l0=0.25)
        cc = Concept(id="cyc-c", slug="cc", title="Cycle C", grade=8, p_l0=0.25)
        memory_db.add_all([ca, cb, cc])
        memory_db.flush()

        # Edges: ca -> cb -> cc -> ca
        memory_db.add_all([
            ConceptEdge(from_concept_id="cyc-a", to_concept_id="cyc-b"),
            ConceptEdge(from_concept_id="cyc-b", to_concept_id="cyc-c"),
            ConceptEdge(from_concept_id="cyc-c", to_concept_id="cyc-a"),
        ])
        memory_db.flush()

        # Query cyc-a with max_depth=10 (well beyond cycle length)
        report = find_root_prerequisite_gap(memory_db, test_student_id, "cyc-a", max_depth=10)

        assert report.has_gaps is True
        gap_ids = [g.concept_id for g in report.all_gaps]
        # Nodes visited backwards from cyc-a: cyc-c (depth 1), cyc-b (depth 2). cyc-a is root so not repeated.
        assert len(gap_ids) == 2
        assert set(gap_ids) == {"cyc-c", "cyc-b"}

    def test_self_referential_loop_handling(self, memory_db, test_student_id):
        """Edge: Self -> Self. Backward traversal must not enter an infinite loop."""
        c = Concept(id="self-loop-node", slug="self", title="Self Node", grade=10, p_l0=0.25)
        memory_db.add(c)
        memory_db.flush()

        memory_db.add(ConceptEdge(from_concept_id="self-loop-node", to_concept_id="self-loop-node"))
        memory_db.flush()

        report = find_root_prerequisite_gap(memory_db, test_student_id, "self-loop-node", max_depth=5)
        # Because self-loop is already in visited set {concept_id}, no ancestors are discovered
        assert report.has_gaps is False
        assert len(report.all_gaps) == 0

    def test_figure_eight_multi_cycle_graph(self, memory_db, test_student_id):
        """Figure-eight cycles: A -> B -> A and A -> C -> A. Must traverse each branch once."""
        ca = Concept(id="fig8-a", slug="fa", title="Center A", grade=10, p_l0=0.25)
        cb = Concept(id="fig8-b", slug="fb", title="Loop B", grade=9, p_l0=0.25)
        cc = Concept(id="fig8-c", slug="fc", title="Loop C", grade=9, p_l0=0.25)
        memory_db.add_all([ca, cb, cc])
        memory_db.flush()

        memory_db.add_all([
            ConceptEdge(from_concept_id="fig8-a", to_concept_id="fig8-b"),
            ConceptEdge(from_concept_id="fig8-b", to_concept_id="fig8-a"),
            ConceptEdge(from_concept_id="fig8-a", to_concept_id="fig8-c"),
            ConceptEdge(from_concept_id="fig8-c", to_concept_id="fig8-a"),
        ])
        memory_db.flush()

        report = find_root_prerequisite_gap(memory_db, test_student_id, "fig8-a", max_depth=5)
        assert report.has_gaps is True
        gap_ids = [g.concept_id for g in report.all_gaps]
        assert set(gap_ids) == {"fig8-b", "fig8-c"}
        assert len(gap_ids) == 2


class TestPrerequisiteDisconnectedAndMasteredGraphs:
    """Tests verifying behavior when concepts have no prerequisites or all are mastered."""

    def test_completely_disconnected_concept_returns_no_gaps(self, memory_db, test_student_id):
        """Concept with zero edges must immediately return has_gaps=False without errors."""
        c = Concept(id="isolated-node", slug="iso", title="Isolated Node", grade=10, p_l0=0.25)
        memory_db.add(c)
        memory_db.flush()

        report = find_root_prerequisite_gap(memory_db, test_student_id, "isolated-node", max_depth=3)
        assert report.has_gaps is False
        assert report.root_gap is None
        assert len(report.all_gaps) == 0
        assert report.explanation == "No prerequisite concepts found for this topic."

    def test_all_prerequisites_fully_mastered_returns_no_gaps(self, memory_db, test_student_id):
        """When student has mastered all prerequisite concepts (p_know >= 0.85, >0 opportunities), no gaps returned."""
        c_parent = Concept(id="mast-parent", slug="mp", title="Mastered Parent", grade=9, p_l0=0.25)
        c_child = Concept(id="mast-child", slug="mc", title="Child Topic", grade=10, p_l0=0.25)
        memory_db.add_all([c_parent, c_child])
        memory_db.add(ConceptEdge(from_concept_id="mast-parent", to_concept_id="mast-child"))
        memory_db.flush()

        # Parent is mastered
        bkt = BktState(
            student_id=test_student_id,
            concept_id="mast-parent",
            p_know=0.92,
            total_opportunities=5,
            correct_count=5,
            is_gap=False,
            gap_signal_count=0,
            mastery_band="mastered",
        )
        memory_db.add(bkt)
        memory_db.flush()

        report = find_root_prerequisite_gap(memory_db, test_student_id, "mast-child", max_depth=3)
        assert report.has_gaps is False
        assert report.root_gap is None
        assert len(report.all_gaps) == 0
        assert report.explanation == "All prerequisite concepts are adequately mastered."


class TestPrerequisiteFoundationBridgePrioritization:
    """Stress tests verifying that foundation bridge concepts (grade < 10) are consistently prioritized."""

    def test_foundation_bridge_prioritized_over_same_depth_grade_10(self, memory_db, test_student_id):
        """Target has two unmastered prerequisites at depth 1: Grade 9 (foundation) vs Grade 10."""
        target = Concept(id="fb-target", slug="fbt", title="Target Topic", grade=10, p_l0=0.25)
        prereq_g10 = Concept(id="fb-prereq-g10", slug="g10", title="Grade 10 Topic", grade=10, p_l0=0.25)
        prereq_g9 = Concept(id="fb-prereq-g9", slug="g9", title="Grade 9 Topic", grade=9, p_l0=0.25)
        memory_db.add_all([target, prereq_g10, prereq_g9])
        memory_db.flush()

        memory_db.add_all([
            ConceptEdge(from_concept_id="fb-prereq-g10", to_concept_id="fb-target"),
            ConceptEdge(from_concept_id="fb-prereq-g9", to_concept_id="fb-target"),
        ])
        memory_db.flush()

        # Both unmastered with identical p_know
        memory_db.add_all([
            BktState(student_id=test_student_id, concept_id="fb-prereq-g10", p_know=0.30, total_opportunities=2, is_gap=False),
            BktState(student_id=test_student_id, concept_id="fb-prereq-g9", p_know=0.30, total_opportunities=2, is_gap=False),
        ])
        memory_db.flush()

        report = find_root_prerequisite_gap(memory_db, test_student_id, "fb-target", max_depth=3)
        assert report.has_gaps is True
        assert report.root_gap is not None
        assert report.root_gap.concept_id == "fb-prereq-g9"
        assert report.root_gap.is_foundation is True
        assert report.root_gap.grade == 9

        # Verify priority scores: Grade 9 has +50 foundation bonus
        g9_gap = next(g for g in report.all_gaps if g.concept_id == "fb-prereq-g9")
        g10_gap = next(g for g in report.all_gaps if g.concept_id == "fb-prereq-g10")
        assert g9_gap.priority_score - g10_gap.priority_score == 50.0

    def test_deeper_foundation_bridge_prioritized_over_shallow_grade_10(self, memory_db, test_student_id):
        """Grade 8 at depth 2 must be prioritized over Grade 10 at depth 1."""
        target = Concept(id="poly-quad", slug="quad", title="Quadratics", grade=10, p_l0=0.25)
        prereq_g10 = Concept(id="poly-linear", slug="lin", title="Linear Systems", grade=10, p_l0=0.25)
        prereq_g9 = Concept(id="poly-g9", slug="pg9", title="Poly Basics", grade=9, p_l0=0.25)
        prereq_g8 = Concept(id="poly-g8", slug="pg8", title="Algebra Basics Grade 8", grade=8, p_l0=0.25)
        memory_db.add_all([target, prereq_g10, prereq_g9, prereq_g8])
        memory_db.flush()

        # Edges: g8 -> g9 -> target; g10 -> target
        memory_db.add_all([
            ConceptEdge(from_concept_id="poly-linear", to_concept_id="poly-quad"),
            ConceptEdge(from_concept_id="poly-g9", to_concept_id="poly-quad"),
            ConceptEdge(from_concept_id="poly-g8", to_concept_id="poly-g9"),
        ])
        memory_db.flush()

        # g10 is unmastered at depth 1; g8 is unmastered at depth 2; g9 is mastered
        memory_db.add_all([
            BktState(student_id=test_student_id, concept_id="poly-linear", p_know=0.20, total_opportunities=2, is_gap=False),
            BktState(student_id=test_student_id, concept_id="poly-g9", p_know=0.90, total_opportunities=5, is_gap=False),
            BktState(student_id=test_student_id, concept_id="poly-g8", p_know=0.20, total_opportunities=2, is_gap=False),
        ])
        memory_db.flush()

        report = find_root_prerequisite_gap(memory_db, test_student_id, "poly-quad", max_depth=3)
        assert report.has_gaps is True
        assert report.root_gap is not None
        assert report.root_gap.concept_id == "poly-g8"
        assert report.root_gap.grade == 8
        assert report.root_gap.depth == 2

    def test_foundation_bridge_with_higher_pknow_still_beats_grade_10(self, memory_db, test_student_id):
        """Grade 9 (p_know=0.45) still beats Grade 10 (p_know=0.10) due to 50pt foundation bonus."""
        target = Concept(id="bridge-target", slug="bt", title="Target", grade=10, p_l0=0.25)
        g10 = Concept(id="bridge-g10", slug="bg10", title="Grade 10 prereq", grade=10, p_l0=0.25)
        g9 = Concept(id="bridge-g9", slug="bg9", title="Grade 9 bridge", grade=9, p_l0=0.25)
        memory_db.add_all([target, g10, g9])
        memory_db.flush()

        memory_db.add_all([
            ConceptEdge(from_concept_id="bridge-g10", to_concept_id="bridge-target"),
            ConceptEdge(from_concept_id="bridge-g9", to_concept_id="bridge-target"),
        ])
        memory_db.flush()

        # Grade 10 has lower p_know (0.10) than Grade 9 (0.45)
        memory_db.add_all([
            BktState(student_id=test_student_id, concept_id="bridge-g10", p_know=0.10, total_opportunities=2, is_gap=False),
            BktState(student_id=test_student_id, concept_id="bridge-g9", p_know=0.45, total_opportunities=2, is_gap=False),
        ])
        memory_db.flush()

        report = find_root_prerequisite_gap(memory_db, test_student_id, "bridge-target", max_depth=3)
        assert report.has_gaps is True
        # Score g9: 50 + 20 - (0.45 * 50) = 47.5
        # Score g10: 0 + 20 - (0.10 * 50) = 15.0
        assert report.root_gap.concept_id == "bridge-g9"


class TestPrerequisiteFallbackAndRobustness:
    """Stress tests verifying defensive fallback under database errors and non-existent concepts."""

    def test_db_exception_falls_back_gracefully_to_manifest(self, test_student_id):
        """When DB query raises an exception, service falls back to manifest.json without crashing."""
        broken_db = MagicMock()
        broken_db.query.side_effect = RuntimeError("Simulated DB connection failure")

        report = find_root_prerequisite_gap(
            db=broken_db,
            student_id=test_student_id,
            concept_id="cbse-10-math-real-numbers-euclid",
            max_depth=3,
        )
        assert report.has_gaps is True
        assert report.root_gap is not None
        assert report.root_gap.grade < 10

    def test_nonexistent_concept_returns_no_gaps(self, memory_db, test_student_id):
        """Querying a non-existent concept ID returns has_gaps=False cleanly."""
        report = find_root_prerequisite_gap(
            db=memory_db,
            student_id=test_student_id,
            concept_id="non-existent-concept-xyz-999",
            max_depth=3,
        )
        assert report.has_gaps is False
        assert report.root_gap is None
        assert report.explanation == "No prerequisite concepts found for this topic."
