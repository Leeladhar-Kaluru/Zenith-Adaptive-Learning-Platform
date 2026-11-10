"""Bayesian Knowledge Tracing (BKT) Engine for ZENITH.

100% deterministic mathematical model tracking learner concept mastery.
Pure math calculations with zero LLM dependencies (Requirement 11).

Formulas:
- Prior Probability: P(L0) = 0.25
- Transition / Learning Probability: P(T) = 0.15
- Guess Probability: P(G) = 0.20
- Slip Probability: P(S) = 0.10

Conditional Posteriors:
- Correct: P(L_t | correct) = (P(L_{t-1}) * (1 - P(S))) / (P(L_{t-1}) * (1 - P(S)) + (1 - P(L_{t-1})) * P(G))
  With hint penalty: max(P(L_{t-1}), P(L_t | correct) - 0.15)
- Incorrect: P(L_t | incorrect) = (P(L_{t-1}) * P(S)) / (P(L_{t-1}) * P(S) + (1 - P(L_{t-1})) * (1 - P(G)))

Transition:
- P(L_t) = P(L_t | obs) + (1 - P(L_t | obs)) * P(T)

Mastery Bands:
- P(L_t) >= 0.85 -> "mastered"
- P(L_t) > 0.25  -> "practicing"
- P(L_t) <= 0.25 -> "not_started"
(Zero attempts: "not_enough_evidence")

Gap Detection:
- 2 consecutive failures -> confirmed gap (is_gap = True).
"""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.mastery import BktState, BktEvent
from app.models.library import Concept

DEFAULT_P_L0 = 0.25
DEFAULT_P_T = 0.15
DEFAULT_P_G = 0.20
DEFAULT_P_S = 0.10
MASTERY_THRESHOLD = 0.85
PRACTICING_THRESHOLD = 0.25
HINT_PENALTY = 0.15


@dataclass
class BktParameters:
    p_l0: float = DEFAULT_P_L0
    p_t: float = DEFAULT_P_T
    p_g: float = DEFAULT_P_G
    p_s: float = DEFAULT_P_S


@dataclass
class BktUpdateResult:
    prior_p_know: float
    posterior_p_know: float
    post_p_know: float
    mastery_band: str
    is_gap: bool
    gap_signal_count: int
    streak: int
    total_opportunities: int
    correct_count: int


def classify_mastery_band(p_know: float, total_opportunities: int = 1) -> str:
    """Classifies numeric mastery estimate into canonical mastery bands."""
    if total_opportunities == 0:
        return "not_enough_evidence"
    if p_know >= MASTERY_THRESHOLD:
        return "mastered"
    if p_know > PRACTICING_THRESHOLD:
        return "practicing"
    return "not_started"


def compute_bkt_update(
    prior_p_know: float,
    is_correct: bool,
    hint_used: bool = False,
    params: Optional[BktParameters] = None,
    current_gap_signal_count: int = 0,
    current_streak: int = 0,
) -> Tuple[float, float, str, bool, int, int]:
    """Pure mathematical BKT update step without database side effects.
    
    Returns:
        (posterior_obs, final_p_know, mastery_band, is_gap, new_gap_signals, new_streak)
    """
    if params is None:
        params = BktParameters()

    prior = max(0.0001, min(0.9999, prior_p_know))
    p_s = max(0.0001, min(0.9999, params.p_s))
    p_g = max(0.0001, min(0.9999, params.p_g))
    p_t = max(0.0001, min(0.9999, params.p_t))

    if is_correct:
        num = prior * (1.0 - p_s)
        den = num + (1.0 - prior) * p_g
        p_obs = num / max(den, 1e-9)

        if hint_used:
            # Hint penalty applied to posterior observation
            p_obs = max(prior, p_obs - HINT_PENALTY)

        new_streak = current_streak + 1
        new_gap_signals = max(0, current_gap_signal_count - 1)
    else:
        num = prior * p_s
        den = num + (1.0 - prior) * (1.0 - p_g)
        p_obs = num / max(den, 1e-9)

        new_streak = 0
        new_gap_signals = current_gap_signal_count + 1

    # Transition step: student may learn during the problem attempt
    p_trans = p_obs + (1.0 - p_obs) * p_t
    final_p_know = round(max(0.0001, min(0.9999, p_trans)), 6)

    # Gap detection logic: 2 consecutive failures -> confirmed gap
    if not is_correct:
        is_gap = new_gap_signals >= 2
    else:
        # Clearance: if mastered or sustained streak >= 2, clear gap
        if final_p_know >= MASTERY_THRESHOLD or new_streak >= 2:
            is_gap = False
        else:
            is_gap = current_gap_signal_count >= 2 and new_gap_signals >= 2

    band = classify_mastery_band(final_p_know, total_opportunities=1)
    return p_obs, final_p_know, band, is_gap, new_gap_signals, new_streak


def get_or_create_bkt_state(
    db: Session,
    student_id: uuid.UUID,
    concept_id: str,
) -> BktState:
    """Retrieves existing BktState or initializes default prior state for concept."""
    state = (
        db.query(BktState)
        .filter(BktState.student_id == student_id, BktState.concept_id == concept_id)
        .first()
    )
    if state is not None:
        return state

    # Check if concept defines custom initial prior p_l0
    concept = db.query(Concept).filter(Concept.id == concept_id).first()
    p_l0 = float(concept.p_l0) if concept and concept.p_l0 is not None else DEFAULT_P_L0

    state = BktState(
        id=uuid.uuid4(),
        student_id=student_id,
        concept_id=concept_id,
        p_know=p_l0,
        total_opportunities=0,
        correct_count=0,
        streak=0,
        mastery_band="not_enough_evidence",
        is_gap=False,
        gap_signal_count=0,
        last_updated_at=datetime.datetime.utcnow(),
    )
    db.add(state)
    db.flush()
    return state


def record_bkt_observation(
    db: Session,
    student_id: uuid.UUID,
    concept_id: str,
    is_correct: bool,
    hint_used: bool = False,
    attempt_id: Optional[uuid.UUID] = None,
) -> BktUpdateResult:
    """Updates BKT state and creates an immutable audit event in bkt_events."""
    state = get_or_create_bkt_state(db, student_id, concept_id)

    # Fetch concept custom parameters if available
    concept = db.query(Concept).filter(Concept.id == concept_id).first()
    params = BktParameters(
        p_l0=float(concept.p_l0) if concept and concept.p_l0 is not None else DEFAULT_P_L0,
        p_t=float(concept.p_t) if concept and concept.p_t is not None else DEFAULT_P_T,
        p_g=float(concept.p_g) if concept and concept.p_g is not None else DEFAULT_P_G,
        p_s=float(concept.p_s) if concept and concept.p_s is not None else DEFAULT_P_S,
    )

    prior_p = state.p_know
    p_obs, post_p, band, is_gap, new_gap_signals, new_streak = compute_bkt_update(
        prior_p_know=prior_p,
        is_correct=is_correct,
        hint_used=hint_used,
        params=params,
        current_gap_signal_count=state.gap_signal_count,
        current_streak=state.streak,
    )

    # Update state fields
    state.total_opportunities += 1
    if is_correct:
        state.correct_count += 1
    state.p_know = post_p
    state.streak = new_streak
    state.gap_signal_count = new_gap_signals
    state.is_gap = is_gap
    state.mastery_band = band
    state.last_updated_at = datetime.datetime.utcnow()

    # Log immutable BktEvent
    event = BktEvent(
        id=uuid.uuid4(),
        student_id=student_id,
        concept_id=concept_id,
        opportunity_number=state.total_opportunities,
        correct=is_correct,
        prior_p_know=prior_p,
        post_p_know=post_p,
        attempt_id=attempt_id,
        hint_used=hint_used,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(event)
    db.flush()

    return BktUpdateResult(
        prior_p_know=prior_p,
        posterior_p_know=p_obs,
        post_p_know=post_p,
        mastery_band=band,
        is_gap=is_gap,
        gap_signal_count=new_gap_signals,
        streak=new_streak,
        total_opportunities=state.total_opportunities,
        correct_count=state.correct_count,
    )
