"""Adversarial stress-testing suite for Bayesian Knowledge Tracing (BKT).

Empirical verification of:
1. Numerical stability under 1000 consecutive correct & 1000 consecutive incorrect responses.
2. Hint penalty gaming resistance and mastery inflation defense.
3. Custom parameter convergence with non-default parameter vectors.
4. Requirement 11 compliance: Zero imports of AI/LLM/HTTP libraries in bkt.py.
5. Boundary and edge-case inputs (negative, over-unity, extreme parameters).
"""
from __future__ import annotations

import ast
import math
import sys
import uuid
from typing import List

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID

@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "TEXT"

from app.models.base import Base
from app.models.library import Concept
from app.models.mastery import BktState, BktEvent
from app.services.bkt import (
    BktParameters,
    compute_bkt_update,
    classify_mastery_band,
    get_or_create_bkt_state,
    record_bkt_observation,
    DEFAULT_P_L0,
    DEFAULT_P_T,
    DEFAULT_P_G,
    DEFAULT_P_S,
    MASTERY_THRESHOLD,
    PRACTICING_THRESHOLD,
    HINT_PENALTY,
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


class TestBktNumericalStability:
    """Stress tests verifying numerical bounds and preventing floating point overflows/underflows."""

    def test_1000_consecutive_correct_responses(self):
        """1000 consecutive correct answers must not exceed 0.9999, blow up to inf, or produce NaN."""
        p = DEFAULT_P_L0
        streak = 0
        signals = 0

        for i in range(1000):
            p_obs, p, band, is_gap, signals, streak = compute_bkt_update(
                prior_p_know=p,
                is_correct=True,
                hint_used=False,
                current_streak=streak,
                current_gap_signal_count=signals,
            )

            assert not math.isnan(p), f"NaN produced at step {i + 1}"
            assert not math.isinf(p), f"Inf produced at step {i + 1}"
            assert not math.isnan(p_obs), f"p_obs NaN produced at step {i + 1}"
            assert 0.0001 <= p <= 0.9999, f"P(know) {p} violated bounds at step {i + 1}"
            assert streak == i + 1, f"Streak desynchronized at step {i + 1}"
            assert signals == 0, f"Gap signals remained non-zero at step {i + 1}"
            assert not is_gap, f"is_gap True during correct streak at step {i + 1}"

        assert p == 0.9999
        assert streak == 1000
        assert band == "mastered"

    def test_1000_consecutive_incorrect_responses(self):
        """1000 consecutive incorrect answers must not underflow below 0.0001, go negative, or produce NaN."""
        p = DEFAULT_P_L0
        streak = 0
        signals = 0

        for i in range(1000):
            p_obs, p, band, is_gap, signals, streak = compute_bkt_update(
                prior_p_know=p,
                is_correct=False,
                current_streak=streak,
                current_gap_signal_count=signals,
            )

            assert not math.isnan(p), f"NaN produced at step {i + 1}"
            assert not math.isinf(p), f"Inf produced at step {i + 1}"
            assert not math.isnan(p_obs), f"p_obs NaN produced at step {i + 1}"
            assert 0.0001 <= p <= 0.9999, f"P(know) {p} violated bounds at step {i + 1}"
            assert streak == 0, f"Streak non-zero during error streak at step {i + 1}"
            assert signals == i + 1, f"Gap signals desynchronized at step {i + 1}"

            if i >= 1:
                assert is_gap is True, f"is_gap False despite >= 2 errors at step {i + 1}"

        # In BKT with transition P(T) = 0.15, steady state under continuous errors is ~0.171429
        assert round(p, 4) == 0.1714
        assert signals == 1000
        assert is_gap is True
        assert band == "not_started"

    def test_1000_alternating_responses_oscillation_stability(self):
        """1000 alternating correct/incorrect responses must oscillate stably without diverging."""
        p = DEFAULT_P_L0
        streak = 0
        signals = 0

        for i in range(1000):
            is_corr = (i % 2 == 0)
            _, p, band, is_gap, signals, streak = compute_bkt_update(
                prior_p_know=p,
                is_correct=is_corr,
                current_streak=streak,
                current_gap_signal_count=signals,
            )
            assert not math.isnan(p) and not math.isinf(p)
            assert 0.0001 <= p <= 0.9999

            if is_corr:
                assert streak == 1
                assert signals == 0
            else:
                assert streak == 0
                assert signals == 1
                # 1 error should NEVER trigger a confirmed gap
                assert is_gap is False

    @pytest.mark.parametrize("extreme_prior", [-100.0, -1.0, 0.0, 1.0, 2.0, 999.0])
    def test_boundary_priors_are_strictly_clamped(self, extreme_prior):
        """Boundary prior inputs outside [0.0001, 0.9999] are clamped safely."""
        _, p_corr, _, _, _, _ = compute_bkt_update(extreme_prior, is_correct=True)
        assert 0.0001 <= p_corr <= 0.9999
        assert not math.isnan(p_corr) and not math.isinf(p_corr)

        _, p_inc, _, _, _, _ = compute_bkt_update(extreme_prior, is_correct=False)
        assert 0.0001 <= p_inc <= 0.9999
        assert not math.isnan(p_inc) and not math.isinf(p_inc)

    def test_extreme_boundary_parameters_division_by_zero_prevention(self):
        """Zero and one parameter vectors must not trigger division by zero or NaN."""
        zero_params = BktParameters(p_l0=0.0, p_t=0.0, p_g=0.0, p_s=0.0)
        _, p1, _, _, _, _ = compute_bkt_update(0.25, is_correct=True, params=zero_params)
        assert 0.0001 <= p1 <= 0.9999
        assert not math.isnan(p1)

        one_params = BktParameters(p_l0=1.0, p_t=1.0, p_g=1.0, p_s=1.0)
        _, p2, _, _, _, _ = compute_bkt_update(0.25, is_correct=False, params=one_params)
        assert 0.0001 <= p2 <= 0.9999
        assert not math.isnan(p2)


class TestBktHintPenaltyGaming:
    """Stress tests verifying that hints discount mastery and prevent gaming/inflation."""

    def test_hint_penalty_strictly_discounts_mastery_trajectory(self):
        """Comparing unassisted vs alternating with hints vs all-hinted trajectories."""
        n_steps = 10

        # Trajectory 1: All unassisted correct
        traj_unassisted: List[float] = [DEFAULT_P_L0]
        p = DEFAULT_P_L0
        for _ in range(n_steps):
            _, p, _, _, _, _ = compute_bkt_update(p, is_correct=True, hint_used=False)
            traj_unassisted.append(p)

        # Trajectory 2: Alternating hinted / unassisted
        traj_alt: List[float] = [DEFAULT_P_L0]
        p = DEFAULT_P_L0
        for i in range(n_steps):
            hint = (i % 2 == 0)
            _, p, _, _, _, _ = compute_bkt_update(p, is_correct=True, hint_used=hint)
            traj_alt.append(p)

        # Trajectory 3: All hinted correct
        traj_hinted: List[float] = [DEFAULT_P_L0]
        p = DEFAULT_P_L0
        for _ in range(n_steps):
            _, p, _, _, _, _ = compute_bkt_update(p, is_correct=True, hint_used=True)
            traj_hinted.append(p)

        # Monotonicity checks: unassisted >= alternating >= all-hinted
        for step in range(1, n_steps + 1):
            assert traj_unassisted[step] >= traj_alt[step], (
                f"Step {step}: Alternating ({traj_alt[step]}) exceeded Unassisted ({traj_unassisted[step]})"
            )
            assert traj_alt[step] >= traj_hinted[step], (
                f"Step {step}: Hinted ({traj_hinted[step]}) exceeded Alternating ({traj_alt[step]})"
            )
            assert traj_unassisted[step] > traj_hinted[step], (
                f"Step {step}: Unassisted ({traj_unassisted[step]}) did not strictly exceed Hinted ({traj_hinted[step]})"
            )

    def test_mastery_inflation_prevention_speed(self):
        """Unassisted correct achieves mastery (>=0.85) in 2 steps; hinted requires 5 steps."""
        p_unassisted = DEFAULT_P_L0
        steps_unassisted = 0
        for _ in range(20):
            _, p_unassisted, band, _, _, _ = compute_bkt_update(p_unassisted, is_correct=True, hint_used=False)
            steps_unassisted += 1
            if band == "mastered":
                break

        p_hinted = DEFAULT_P_L0
        steps_hinted = 0
        for _ in range(20):
            _, p_hinted, band, _, _, _ = compute_bkt_update(p_hinted, is_correct=True, hint_used=True)
            steps_hinted += 1
            if band == "mastered":
                break

        assert steps_unassisted == 2, f"Unassisted required {steps_unassisted} steps, expected 2"
        assert steps_hinted == 5, f"Hinted required {steps_hinted} steps, expected 5"
        assert steps_hinted >= 2.5 * steps_unassisted, "Hint penalty did not sufficiently delay mastery"

    def test_hint_penalty_does_not_drop_below_prior(self):
        """Applying hint penalty on a correct answer never drops P(obs) below previous prior."""
        for prior in [0.10, 0.25, 0.50, 0.75, 0.90]:
            p_obs, p_trans, _, _, _, _ = compute_bkt_update(prior, is_correct=True, hint_used=True)
            assert p_obs >= prior, f"p_obs {p_obs} dropped below prior {prior}"
            assert p_trans >= prior, f"p_trans {p_trans} dropped below prior {prior}"


class TestBktCustomParametersConvergence:
    """Stress tests using non-default and adversarial parameter vectors."""

    def test_custom_parameters_convergence(self):
        """Verifies convergence with dispatch specified non-default parameters:
        P(L0)=0.05, P(T)=0.01, P(G)=0.4, P(S)=0.3.
        """
        params = BktParameters(p_l0=0.05, p_t=0.01, p_g=0.4, p_s=0.3)

        # 1. Convergence under consecutive correct responses
        p = params.p_l0
        streak = 0
        for i in range(100):
            _, p, band, _, _, streak = compute_bkt_update(
                p, is_correct=True, params=params, current_streak=streak
            )
            assert not math.isnan(p) and not math.isinf(p)
            assert 0.0001 <= p <= 0.9999

        assert p >= MASTERY_THRESHOLD
        assert band == "mastered"
        assert streak == 100

        # 2. Convergence under consecutive incorrect responses
        p = params.p_l0
        signals = 0
        for i in range(100):
            _, p, band, is_gap, signals, _ = compute_bkt_update(
                p, is_correct=False, params=params, current_gap_signal_count=signals
            )
            assert not math.isnan(p) and not math.isinf(p)
            assert 0.0001 <= p <= 0.9999

        # With P(T)=0.01, steady state error is ~0.02
        assert round(p, 4) == 0.0200
        assert p < PRACTICING_THRESHOLD
        assert is_gap is True
        assert band == "not_started"
        assert signals == 100

    def test_high_guess_low_slip_demands_more_evidence(self):
        """When P(G)=0.80 (easy to guess), a single correct answer provides little evidence."""
        params_high_guess = BktParameters(p_l0=0.25, p_t=0.10, p_g=0.80, p_s=0.05)
        params_standard = BktParameters(p_l0=0.25, p_t=0.10, p_g=0.20, p_s=0.05)

        _, p_high_guess, _, _, _, _ = compute_bkt_update(0.25, is_correct=True, params=params_high_guess)
        _, p_standard, _, _, _, _ = compute_bkt_update(0.25, is_correct=True, params=params_standard)

        assert p_high_guess < p_standard
        assert p_high_guess < 0.40  # Belief gain is severely dampened by high guess rate


class TestBktRequirement11ZeroLlmImports:
    """Verifies Requirement 11: BKT module has ZERO imports of AI/LLM/HTTP libraries."""

    def test_ast_inspection_for_forbidden_imports(self):
        """Scans the AST of bkt.py for any forbidden AI or external networking packages."""
        import app.services.bkt as bkt_module
        source_path = bkt_module.__file__

        with open(source_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=source_path)

        imported_modules: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imported_modules.append(f"{mod}.{alias.name}" if mod else alias.name)

        forbidden_tokens = [
            "ai_provider",
            "openai",
            "httpx",
            "groq",
            "anthropic",
            "langchain",
            "llama",
            "lmstudio",
            "requests",
            "urllib",
            "aiohttp",
        ]

        violations = [
            imp for imp in imported_modules
            if any(forbidden in imp.lower() for forbidden in forbidden_tokens)
        ]

        assert len(violations) == 0, (
            f"Requirement 11 VIOLATION: Forbidden AI/HTTP imports detected in bkt.py: {violations}"
        )

    def test_bkt_module_has_zero_llm_symbols_in_namespace(self):
        """Ensures that no AI provider or LLM symbols exist in the runtime namespace of bkt."""
        import app.services.bkt as bkt_mod
        forbidden_attrs = ["ai_provider", "openai", "httpx", "Groq", "OpenAI", "generate_chat"]
        for attr in forbidden_attrs:
            assert not hasattr(bkt_mod, attr), f"Forbidden symbol '{attr}' found in bkt module namespace"


class TestBktDatabaseIntegrationStress:
    """Verifies persistent database state operations with custom parameters and audit logging."""

    def test_record_bkt_observation_atomic_and_respects_custom_concept_params(
        self, memory_db, test_student_id
    ):
        """Ensures record_bkt_observation reads custom concept parameters and logs BktEvents."""
        custom_concept = Concept(
            id="concept-custom-bkt",
            slug="custom-bkt",
            title="Custom BKT Concept",
            grade=10,
            p_l0=0.05,
            p_t=0.02,
            p_g=0.35,
            p_s=0.25,
        )
        memory_db.add(custom_concept)
        memory_db.flush()

        # Step 1: Initial observation (correct)
        res1 = record_bkt_observation(
            memory_db, test_student_id, "concept-custom-bkt", is_correct=True
        )
        assert res1.prior_p_know == 0.05
        assert res1.total_opportunities == 1
        assert res1.correct_count == 1
        assert res1.streak == 1

        state = (
            memory_db.query(BktState)
            .filter(
                BktState.student_id == test_student_id,
                BktState.concept_id == "concept-custom-bkt",
            )
            .first()
        )
        assert state is not None
        assert state.p_know == res1.post_p_know

        # Step 2: 50 sequential updates verifying event log integrity
        for step in range(2, 52):
            is_c = (step % 3 != 0)
            res = record_bkt_observation(
                memory_db, test_student_id, "concept-custom-bkt", is_correct=is_c
            )
            assert res.total_opportunities == step

        events = (
            memory_db.query(BktEvent)
            .filter(
                BktEvent.student_id == test_student_id,
                BktEvent.concept_id == "concept-custom-bkt",
            )
            .order_by(BktEvent.opportunity_number)
            .all()
        )
        assert len(events) == 51
        for idx, ev in enumerate(events, start=1):
            assert ev.opportunity_number == idx
