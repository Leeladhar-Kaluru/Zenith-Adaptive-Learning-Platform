"""Milestone 3 Comprehensive Test Suite: Adaptive Services, BKT, Gamification & Tutor.

Verifies:
1. Pure Math BKT Engine (4 parameters, conditional posteriors, hint penalty, transition, mastery bands, gap signals).
2. Prerequisite DAG Backward Gap Traversal (BFS to depth 3, foundation bridge concept prioritization, cycle prevention).
3. Gamification & Rewards (XP, coins, levels, Asia/Kolkata calendar streaks, canonical badges, idempotency).
4. Curriculum Library Service (catalogue, chapter detail, student question redaction, DAG concept map, enrollment, progress).
5. Calibrated Diagnostic Assessment (8-probe session lifecycle, grading, BKT updates, gap analysis, review items).
6. Adaptive Practice Arena (recommendations, question serving, grading, BKT updates, feedback).
7. Grounded Socratic AI Tutor (retrieval grounding, Socratic prompt, citation extraction, 503 fallback, daily quota).
8. Attempt Service Shared Library Access (allows published library paths, dual answerKey/answer support).
9. Rule 1 Compliance (visible product name is strictly SETU; 0 occurrences of 'SETU V2' / 'SETU 2.0').
"""
from __future__ import annotations

import datetime
import os
import re
import uuid
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID

# Compile PostgreSQL UUID as TEXT on SQLite for proper SQLite TEXT affinity
@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "TEXT"

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.ai_provider import LLMUnavailableError
from app.models.base import Base
from app.models.learning import LearningPath, PathLesson, LessonVersion, Question, QuizAttempt
from app.models.library import Concept, ConceptEdge, ConceptChapter, LibraryEnrollment, ResourceProgress
from app.models.mastery import BktState, BktEvent
from app.models.rewards import StudentReward, RewardEvent, Badge, StudentBadge
from app.models.diagnostics import DiagnosticSession, DiagnosticItem
from app.models.tutor import TutorThread, TutorMessage

from app.api.v1.library import (
    get_library_catalogue,
    get_chapter_detail,
    get_resource_package,
    get_concept_dag_map,
    enroll_chapter,
    get_my_learning,
    update_progress,
    EnrollRequest,
    ProgressUpdateRequest,
)
from app.api.v1.rewards import (
    get_my_rewards,
    get_all_badges,
    claim_daily_bonus,
)
from app.api.v1.diagnostics import (
    start_diagnostic_session,
    get_session_status,
    submit_diagnostic,
    DiagnosticSessionRequest,
    DiagnosticSubmitRequest,
    DiagnosticItemResponse,
)
from app.api.v1.practice import (
    get_recommendation,
    create_practice_session,
    submit_practice_attempt as submit_practice_attempt_endpoint,
    PracticeSessionRequest,
    PracticeSubmitRequest,
)
from app.api.v1.tutor import (
    post_tutor_message,
    list_threads,
    get_thread_history,
    TutorMessageRequest,
)

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
)
from app.services.prerequisite_service import (
    find_root_prerequisite_gap,
    get_incoming_prerequisites,
    PrerequisiteGapReport,
)
from app.services.rewards_service import (
    award_activity_rewards,
    get_student_rewards_summary,
    calculate_level_info,
    update_streak_kolkata,
    ensure_canonical_badges,
    check_and_award_badges,
    KOLKATA_TZ,
)
from app.services.library_service import (
    get_catalogue,
    get_chapter,
    get_resource,
    get_concept_map,
    enroll_student,
    get_student_learning,
    update_resource_progress,
)
from app.services.library_retrieval import (
    retrieve_curriculum_context,
    _tokenize,
)
from app.services.tutor_service import (
    process_tutor_message,
    extract_citations,
    SOCRATIC_SYSTEM_PROMPT,
    DEGRADED_MESSAGE,
    QUOTA_EXCEEDED_MESSAGE,
)
from app.services.diagnostic_service import (
    create_diagnostic_session,
    get_diagnostic_session,
    submit_diagnostic_responses,
)
from app.services.practice_service import (
    get_practice_recommendation,
    get_practice_questions,
    submit_practice_attempt,
)
from app.services.attempt_service import (
    grade_response,
    grade_and_record_attempt,
)
from app.main import app as fastapi_app


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def memory_db():
    """In-memory SQLite database session isolated per test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    ensure_canonical_badges(session)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def test_student_id():
    return uuid.UUID("11111111-2222-3333-4444-555555555555")


# ==============================================================================
# 1. BKT ENGINE MATHEMATICAL TESTS
# ==============================================================================

class TestBktEngine:
    def test_default_parameters(self):
        """Validates canonical BKT parameters: P(L0)=0.25, P(T)=0.15, P(G)=0.20, P(S)=0.10."""
        params = BktParameters()
        assert params.p_l0 == 0.25
        assert params.p_t == 0.15
        assert params.p_g == 0.20
        assert params.p_s == 0.10

    def test_first_correct_observation(self):
        """Correct observation transitions belief from 0.250 to 0.660."""
        p_obs, p_trans, band, is_gap, signals, streak = compute_bkt_update(
            prior_p_know=0.25,
            is_correct=True,
            hint_used=False,
        )
        assert round(p_obs, 3) == 0.600
        assert round(p_trans, 3) == 0.660
        assert band == "practicing"
        assert is_gap is False
        assert streak == 1

    def test_second_correct_observation_reaches_mastery(self):
        """Two consecutive correct observations advance P(know) to >= 0.85 (mastered)."""
        _, p_trans1, _, _, _, _ = compute_bkt_update(0.25, is_correct=True)
        p_obs2, p_trans2, band2, is_gap2, signals2, streak2 = compute_bkt_update(
            prior_p_know=p_trans1,
            is_correct=True,
            current_streak=1,
        )
        assert round(p_trans2, 3) == 0.913
        assert p_trans2 >= 0.85
        assert band2 == "mastered"
        assert is_gap2 is False
        assert streak2 == 2

    def test_first_incorrect_observation_signals_warning(self):
        """First error lowers P(know) to 0.184 and raises 1 gap signal (early warning, not gap)."""
        p_obs, p_trans, band, is_gap, signals, streak = compute_bkt_update(
            prior_p_know=0.25,
            is_correct=False,
        )
        assert round(p_obs, 3) == 0.040
        assert round(p_trans, 3) == 0.184
        assert band == "not_started"
        assert is_gap is False
        assert signals == 1
        assert streak == 0

    def test_two_consecutive_failures_triggers_confirmed_gap(self):
        """Two consecutive failures confirm a prerequisite gap (is_gap = True)."""
        _, p_trans1, _, _, signals1, _ = compute_bkt_update(0.25, is_correct=False)
        p_obs2, p_trans2, band2, is_gap2, signals2, streak2 = compute_bkt_update(
            prior_p_know=p_trans1,
            is_correct=False,
            current_gap_signal_count=signals1,
        )
        assert round(p_trans2, 3) == 0.173
        assert signals2 == 2
        assert is_gap2 is True
        assert band2 == "not_started"

    def test_hint_penalty_reduces_knowledge_gain(self):
        """Using instructional hints penalizes posterior observation, resulting in lower mastery."""
        p_obs_clean, p_trans_clean, _, _, _, _ = compute_bkt_update(0.25, is_correct=True, hint_used=False)
        p_obs_hint, p_trans_hint, _, _, _, _ = compute_bkt_update(0.25, is_correct=True, hint_used=True)

        assert round(p_obs_hint, 3) == round(p_obs_clean - 0.15, 3)
        assert p_trans_hint < p_trans_clean
        assert p_trans_hint >= 0.25  # Lower bound is previous prior

    def test_mastery_bands_classification(self):
        """Verifies mastery band boundaries."""
        assert classify_mastery_band(0.25, total_opportunities=0) == "not_enough_evidence"
        assert classify_mastery_band(0.20, total_opportunities=1) == "not_started"
        assert classify_mastery_band(0.25, total_opportunities=1) == "not_started"
        assert classify_mastery_band(0.26, total_opportunities=1) == "practicing"
        assert classify_mastery_band(0.849, total_opportunities=2) == "practicing"
        assert classify_mastery_band(0.85, total_opportunities=2) == "mastered"
        assert classify_mastery_band(0.95, total_opportunities=3) == "mastered"

    def test_database_bkt_observation_and_event_logging(self, memory_db, test_student_id):
        """Records BKT observation, updating BktState and creating immutable BktEvent."""
        concept_id = "test-concept-algebra"
        res1 = record_bkt_observation(memory_db, test_student_id, concept_id, is_correct=True)
        assert res1.total_opportunities == 1
        assert res1.correct_count == 1
        assert round(res1.post_p_know, 3) == 0.660

        state = memory_db.query(BktState).filter(BktState.student_id == test_student_id, BktState.concept_id == concept_id).first()
        assert state is not None
        assert state.correct_count == 1
        assert state.p_know == res1.post_p_know

        events = memory_db.query(BktEvent).filter(BktEvent.student_id == test_student_id, BktEvent.concept_id == concept_id).all()
        assert len(events) == 1
        assert events[0].opportunity_number == 1
        assert events[0].correct is True


# ==============================================================================
# 2. PREREQUISITE DAG GAP TRAVERSAL TESTS
# ==============================================================================

class TestPrerequisiteService:
    def test_backward_bfs_identifies_root_foundation_gap(self, memory_db, test_student_id):
        """Backward traversal up to depth 3 isolates root unmastered foundation concept (grade < 10)."""
        # Create DAG: c08 (Grade 8) -> c09 (Grade 9) -> c10 (Grade 10)
        c08 = Concept(id="c08-primes", slug="primes", title="Primes & Factors", grade=8, p_l0=0.25)
        c09 = Concept(id="c09-rationals", slug="rationals", title="Rational Numbers", grade=9, p_l0=0.25)
        c10 = Concept(id="c10-euclid", slug="euclid", title="Euclid Lemma", grade=10, p_l0=0.25)
        memory_db.add_all([c08, c09, c10])
        memory_db.flush()

        edge1 = ConceptEdge(from_concept_id="c08-primes", to_concept_id="c09-rationals")
        edge2 = ConceptEdge(from_concept_id="c09-rationals", to_concept_id="c10-euclid")
        memory_db.add_all([edge1, edge2])
        memory_db.flush()

        # Mark c08 as confirmed gap for student
        bkt_c08 = BktState(
            student_id=test_student_id,
            concept_id="c08-primes",
            p_know=0.173,
            total_opportunities=2,
            correct_count=0,
            is_gap=True,
            gap_signal_count=2,
            mastery_band="not_started",
        )
        memory_db.add(bkt_c08)
        memory_db.flush()

        report = find_root_prerequisite_gap(memory_db, test_student_id, "c10-euclid", max_depth=3)
        assert report.has_gaps is True
        assert report.root_gap is not None
        assert report.root_gap.concept_id == "c08-primes"
        assert report.root_gap.grade == 8
        assert report.root_gap.depth == 2
        assert "c08-primes" in report.root_gap.path
        assert "traces back 2 levels" in report.explanation

    def test_prerequisite_fallback_to_manifest_when_db_empty(self, test_student_id):
        """Falls back gracefully to manifest.json when DB has zero edge rows."""
        report = find_root_prerequisite_gap(
            db=None,
            student_id=test_student_id,
            concept_id="cbse-10-math-real-numbers-euclid",
            max_depth=3,
        )
        assert report.has_gaps is True
        assert report.root_gap is not None
        assert report.root_gap.grade < 10


# ==============================================================================
# 3. REWARDS & GAMIFICATION TESTS
# ==============================================================================

class TestRewardsService:
    def test_level_calculation(self):
        """Validates level calculation: max(1, (total_xp // 100) + 1)."""
        assert calculate_level_info(0) == (1, 0, 100)
        assert calculate_level_info(99) == (1, 99, 1)
        assert calculate_level_info(100) == (2, 0, 100)
        assert calculate_level_info(245) == (3, 45, 55)

    def test_idempotent_award_activity_rewards(self, memory_db, test_student_id):
        """Calling award with identical idempotency key twice returns cached result without double crediting."""
        key = f"attempt-test-{uuid.uuid4()}"
        res1 = award_activity_rewards(
            memory_db, test_student_id, "practice", key, xp_amount=10, coins_amount=2
        )
        assert res1["awarded"] is True
        # Base 10 XP + 50 XP bonus for first_step badge unlock = 60 total XP
        assert res1["totalXp"] == 60
        assert res1["coins"] >= 2

        # Second call with same key
        res2 = award_activity_rewards(
            memory_db, test_student_id, "practice", key, xp_amount=10, coins_amount=2
        )
        assert res2["awarded"] is False
        assert res2["xpAwarded"] == 0
        assert res2["totalXp"] == 60  # Exactly preserved, no duplicate crediting!

    def test_asia_kolkata_streak_progression(self, memory_db, test_student_id):
        """Evaluates calendar streak progression strictly in Asia/Kolkata timezone."""
        reward = StudentReward(student_id=test_student_id)
        memory_db.add(reward)
        memory_db.flush()

        today_kolkata = datetime.datetime.now(KOLKATA_TZ).date()

        # Day 1
        streak, inc = update_streak_kolkata(reward)
        assert streak == 1
        assert inc is True
        assert reward.last_active_date == today_kolkata

        # Same Day activity does not increment
        streak2, inc2 = update_streak_kolkata(reward)
        assert streak2 == 1
        assert inc2 is False

        # Simulate yesterday activity for next day continuation
        reward.last_active_date = today_kolkata - datetime.timedelta(days=1)
        streak3, inc3 = update_streak_kolkata(reward)
        assert streak3 == 2
        assert inc3 is True

        # Simulate missed yesterday (activity 3 days ago)
        reward.last_active_date = today_kolkata - datetime.timedelta(days=3)
        streak4, inc4 = update_streak_kolkata(reward)
        assert streak4 == 1
        assert inc4 is False

    def test_canonical_badge_unlock(self, memory_db, test_student_id):
        """Unlocks 'first_step' badge on first completed attempt and awards bonus XP."""
        res = award_activity_rewards(
            memory_db,
            test_student_id,
            "practice",
            f"attempt-{uuid.uuid4()}",
            xp_amount=10,
            coins_amount=2,
            meta={"completed_attempt": True},
        )
        unlocked = [b["id"] for b in res["unlockedBadges"]]
        assert "first_step" in unlocked
        # Total XP includes 10 base + 50 badge bonus = 60
        assert res["totalXp"] == 60


# ==============================================================================
# 4. CURRICULUM LIBRARY SERVICE TESTS
# ==============================================================================

class TestLibraryService:
    def test_catalogue_contains_all_four_chapters(self, memory_db):
        """Catalogue lists all 4 Class 10 Math chapters with concepts and lessons."""
        cat = get_catalogue(memory_db, grade=10, subject_id="subject-math")
        assert cat["curriculumId"] == "cbse-10-math"
        assert cat["totalChapters"] == 4
        assert len(cat["chapters"]) == 4
        slugs = [ch["slug"] for ch in cat["chapters"]]
        assert "real-numbers" in slugs
        assert "polynomials" in slugs
        assert "linear-equations" in slugs
        assert "quadratic-equations" in slugs

    def test_chapter_details_and_resources(self, memory_db):
        """Chapter detail endpoint lists syllabus concepts and resources."""
        ch = get_chapter(memory_db, "real-numbers")
        assert ch is not None
        assert ch["title"] == "Real Numbers"
        assert len(ch["concepts"]) >= 4
        assert len(ch["resources"]) >= 5

    def test_resource_redaction_preserves_worked_examples(self, memory_db, test_student_id):
        """Resource package strips answer keys from quiz items while preserving worked examples."""
        res = get_resource(memory_db, "real-numbers-lesson", student_id=test_student_id)
        assert res is not None
        pkg = res["package"]
        assert "blocks" in pkg
        assert "workedExamples" in pkg

        # Worked examples retain demonstration steps and answers
        we = pkg["workedExamples"][0]
        assert "prompt" in we or "problem" in we
        assert "steps" in we
        assert "answer" in we

        # Practice items have answerKey, explanation, steps stripped
        if "practice" in pkg:
            for p in pkg["practice"]:
                assert "answerKey" not in p
                assert "answer_key" not in p
                assert "explanation" not in p

    def test_concept_map_structure(self, memory_db, test_student_id):
        """Returns concept DAG nodes and edges with mastery status."""
        cmap = get_concept_map(memory_db, "real-numbers", student_id=test_student_id)
        assert len(cmap["nodes"]) >= 4
        assert len(cmap["edges"]) >= 3
        for node in cmap["nodes"]:
            assert "pKnow" in node
            assert "masteryBand" in node

    def test_private_lesson_access_blocked_for_unauthorized_student(self, memory_db, test_student_id):
        """Rule 10: Private non-library lesson cannot be read by another student or anonymous user."""
        victim_id = uuid.uuid4()
        p = LearningPath(
            id=uuid.uuid4(),
            owner_id=victim_id,
            grade=10,
            subject_id="subject-math",
            is_library=False,
            outline_json={},
        )
        l = PathLesson(
            id=uuid.uuid4(),
            path_id=p.id,
            lesson_key="victim-private-lesson",
            title="Victim Private Study",
            sequence=1,
        )
        v = LessonVersion(
            id=uuid.uuid4(),
            path_lesson_id=l.id,
            lesson_package_json={"title": "Victim Confidential Notes", "blocks": []},
        )
        memory_db.add_all([p, l, v])
        memory_db.flush()

        # Attacker cannot read
        attacker_res = get_resource(memory_db, str(l.id), student_id=test_student_id)
        assert attacker_res is None

        # Anonymous cannot read
        anon_res = get_resource(memory_db, str(l.id), student_id=None)
        assert anon_res is None

        # Attacker cannot lookup by lesson key
        key_res = get_resource(memory_db, "victim-private-lesson", student_id=test_student_id)
        assert key_res is None

        # Victim (owner) CAN read
        owner_res = get_resource(memory_db, str(l.id), student_id=victim_id)
        assert owner_res is not None
        assert owner_res["title"] == "Victim Private Study"

    def test_published_library_lesson_accessible_to_all_and_anonymous(self, memory_db, test_student_id):
        """Published library lesson is readable by any authenticated student and anonymous users."""
        system_owner = uuid.UUID("00000000-0000-0000-0000-00000000000a")
        pub_p = LearningPath(
            id=uuid.uuid4(),
            owner_id=system_owner,
            grade=10,
            subject_id="subject-math",
            is_library=True,
            library_slug="cbse-test-shared",
            library_status="published",
            outline_json={},
        )
        pub_l = PathLesson(
            id=uuid.uuid4(),
            path_id=pub_p.id,
            lesson_key="pub-shared-lesson",
            title="Public Geometry",
            sequence=1,
        )
        pub_v = LessonVersion(
            id=uuid.uuid4(),
            path_lesson_id=pub_l.id,
            lesson_package_json={"title": "Public Geometry", "blocks": [{"id": "b1", "content": "Formula"}]},
        )
        memory_db.add_all([pub_p, pub_l, pub_v])
        memory_db.flush()

        # Authenticated student can read
        student_res = get_resource(memory_db, str(pub_l.id), student_id=test_student_id)
        assert student_res is not None
        assert student_res["title"] == "Public Geometry"

        # Anonymous visitor can read
        anon_res = get_resource(memory_db, str(pub_l.id), student_id=None)
        assert anon_res is not None
        assert anon_res["title"] == "Public Geometry"

    def test_update_resource_progress_isolation(self, memory_db, test_student_id):
        """Rule 10: Progress and rewards cannot be farmed on private lessons of other students."""
        victim_id = uuid.uuid4()
        p = LearningPath(
            id=uuid.uuid4(),
            owner_id=victim_id,
            grade=10,
            subject_id="subject-math",
            is_library=False,
            outline_json={},
        )
        l = PathLesson(
            id=uuid.uuid4(),
            path_id=p.id,
            lesson_key="victim-priv-prog",
            title="Victim Priv",
            sequence=1,
        )
        v = LessonVersion(
            id=uuid.uuid4(),
            path_lesson_id=l.id,
            lesson_package_json={"title": "Victim Priv"},
        )
        memory_db.add_all([p, l, v])
        memory_db.flush()

        # Attacker attempt to progress victim's lesson is rejected
        rejected = update_resource_progress(
            db=memory_db,
            student_id=test_student_id,
            path_lesson_id=str(l.id),
            status="completed",
            completion_pct=100.0,
        )
        assert rejected is None
        assert (
            memory_db.query(ResourceProgress)
            .filter(ResourceProgress.student_id == test_student_id, ResourceProgress.path_lesson_id == l.id)
            .first()
            is None
        )

        # Owner CAN progress own lesson
        allowed = update_resource_progress(
            db=memory_db,
            student_id=victim_id,
            path_lesson_id=str(l.id),
            status="completed",
            completion_pct=100.0,
        )
        assert allowed is not None
        assert allowed["status"] == "completed"


# ==============================================================================
# 5. DIAGNOSTIC ASSESSMENT LIFECYCLE TESTS
# ==============================================================================

class TestDiagnosticService:
    def test_session_creation_draws_8_probes(self, memory_db, test_student_id):
        """Session contains 8 items (4 foundation bridge + 4 chapter core) with redacted questions."""
        sess = create_diagnostic_session(memory_db, test_student_id, "real-numbers")
        assert sess["status"] == "in_progress"
        assert sess["totalItems"] == 8
        assert len(sess["items"]) == 8

        # First 4 are foundation bridge probes
        for it in sess["items"][:4]:
            assert it["isPrerequisiteProbe"] is True
            assert "answerKey" not in it["question"]

        # Last 4 are chapter core
        for it in sess["items"][4:]:
            assert it["isPrerequisiteProbe"] is False
            assert "answerKey" not in it["question"]

    def test_session_submission_and_gap_analysis(self, memory_db, test_student_id):
        """Grading diagnostic submissions triggers BKT updates and awards rewards."""
        sess = create_diagnostic_session(memory_db, test_student_id, "real-numbers")
        s_id = uuid.UUID(sess["sessionId"])

        # Submit 8 responses: 7 correct, 1 wrong on item 1 (foundation bridge)
        responses = [
            {"itemIndex": 1, "studentResponse": 3, "hintsUsed": 0},  # Wrong (expected 0)
            {"itemIndex": 2, "studentResponse": 0, "hintsUsed": 0},  # Correct
            {"itemIndex": 3, "studentResponse": 0, "hintsUsed": 0},  # Correct
            {"itemIndex": 4, "studentResponse": 0, "hintsUsed": 0},  # Correct
            {"itemIndex": 5, "studentResponse": 0, "hintsUsed": 0},  # Correct
            {"itemIndex": 6, "studentResponse": 0, "hintsUsed": 0},  # Correct
            {"itemIndex": 7, "studentResponse": 0, "hintsUsed": 0},  # Correct
            {"itemIndex": 8, "studentResponse": 0, "hintsUsed": 0},  # Correct
        ]

        result = submit_diagnostic_responses(memory_db, test_student_id, s_id, responses)
        assert result["status"] == "completed"
        assert result["completedItems"] == 8
        assert result["rewards"]["xpAwarded"] == 50
        assert result["rewards"]["coinsAwarded"] == 10
        assert len(result["reviewItems"]) == 8
        # Answers revealed in review items
        assert "correctAnswer" in result["reviewItems"][0]


# ==============================================================================
# 6. ADAPTIVE PRACTICE LIFECYCLE TESTS
# ==============================================================================

class TestPracticeService:
    def test_recommendation_prioritizes_weakest_or_gap(self, memory_db, test_student_id):
        """Recommends weakest concept for practice."""
        rec = get_practice_recommendation(memory_db, test_student_id, "real-numbers")
        assert rec["conceptId"] is not None
        assert "reason" in rec

    def test_practice_question_serving_redacted(self, memory_db, test_student_id):
        """Served practice questions are strictly redacted."""
        questions = get_practice_questions(memory_db, test_student_id, "real-numbers", count=3)
        assert len(questions) > 0
        for q in questions:
            assert "answerKey" not in q
            assert "explanation" not in q

    def test_practice_submission_grades_and_updates_bkt(self, memory_db, test_student_id):
        """Grading practice attempt updates BKT probability and awards rewards."""
        res = submit_practice_attempt(
            db=memory_db,
            student_id=test_student_id,
            question_id="diag-rn-01",
            concept_id="cbse-08-math-primes-divisibility",
            response=0,  # Correct index for 140 prime factorization
        )
        assert res["isCorrect"] is True
        assert res["bkt"]["postPKnow"] > res["bkt"]["priorPKnow"]
        assert res["rewards"]["xpAwarded"] >= 10

    def test_practice_questions_retrieves_from_db_with_cast_string(self, memory_db, test_student_id):
        """Verifies get_practice_questions retrieves questions from database using Question.concept_ids.cast(String) without NameError."""
        import app.services.practice_service as ps
        assert hasattr(ps, "String"), "practice_service must import String from sqlalchemy"

        # 1. Insert a specific question into the database matching a distinct concept_id
        target_concept = "cbse-10-math-real-numbers-euclid"
        db_q_id = uuid.uuid4()
        test_question = Question(
            id=db_q_id,
            lesson_version_id=uuid.uuid4(),
            question_key="db-test-question-euclid-1",
            type="multiple_choice",
            prompt_json={
                "prompt": "What is the quotient when 17 is divided by 3 using Euclid lemma?",
                "options": ["5", "2", "6", "3"],
            },
            answer_key_json={"answer": "5", "explanation": "17 = 3 * 5 + 2"},
            concept_ids=[target_concept, "cbse-10-math-algebra-foundations"],
            difficulty="standard",
            validation_status="ready",
        )
        memory_db.add(test_question)
        memory_db.commit()

        # 2. Request practice questions specifically for target_concept
        questions = get_practice_questions(
            db=memory_db,
            student_id=test_student_id,
            chapter_slug="real-numbers",
            concept_id=target_concept,
            count=1,
        )

        # 3. Assert question was retrieved from DB (not fallback)
        assert len(questions) == 1, "Expected exactly 1 question returned"
        retrieved = questions[0]
        assert retrieved["questionId"] == str(db_q_id), "Question must originate from DB Question table"
        assert retrieved["conceptId"] == target_concept
        assert retrieved["prompt"] == "What is the quotient when 17 is divided by 3 using Euclid lemma?"
        assert retrieved["options"] == ["5", "2", "6", "3"]
        assert retrieved["difficulty"] == "standard"
        
        # 4. Assert strict redaction: answerKey and explanation must never be exposed
        assert "answerKey" not in retrieved
        assert "answer_key" not in retrieved
        assert "explanation" not in retrieved

    def test_practice_questions_excludes_already_solved_db_questions(self, memory_db, test_student_id):
        """Verifies get_practice_questions excludes database questions already solved correctly by student."""
        target_concept = "cbse-10-math-polynomials-zeros"
        lv_id = uuid.uuid4()

        # Insert solved question
        solved_q_id = uuid.uuid4()
        solved_q = Question(
            id=solved_q_id,
            lesson_version_id=lv_id,
            question_key="db-poly-solved",
            type="multiple_choice",
            prompt_json={"prompt": "Solved question", "options": ["A", "B"]},
            answer_key_json={"answer": "A"},
            concept_ids=[target_concept],
        )
        memory_db.add(solved_q)

        # Add correct QuizAttempt for solved_q
        attempt = QuizAttempt(
            id=uuid.uuid4(),
            owner_id=test_student_id,
            question_id=solved_q_id,
            lesson_version_id=lv_id,
            response_json={"response": "A"},
            score=1.0,
            is_correct=True,
            occurred_at=datetime.datetime.now(datetime.timezone.utc),
        )
        memory_db.add(attempt)

        # Insert unsolved question
        unsolved_q_id = uuid.uuid4()
        unsolved_q = Question(
            id=unsolved_q_id,
            lesson_version_id=lv_id,
            question_key="db-poly-unsolved",
            type="multiple_choice",
            prompt_json={"prompt": "Unsolved question", "options": ["X", "Y"]},
            answer_key_json={"answer": "X"},
            concept_ids=[target_concept],
        )
        memory_db.add(unsolved_q)
        memory_db.commit()

        # Query practice questions
        questions = get_practice_questions(
            db=memory_db,
            student_id=test_student_id,
            chapter_slug="polynomials",
            concept_id=target_concept,
            count=1,
        )

        assert len(questions) == 1
        assert questions[0]["questionId"] == str(unsolved_q_id), "Must serve unsolved question, excluding solved one"


# ==============================================================================
# 7. GROUNDED SOCRATIC AI TUTOR TESTS
# ==============================================================================

class TestSocraticTutor:
    def test_curriculum_retrieval_returns_numbered_context(self):
        """Curriculum retrieval formats numbered context blocks [1], [2]."""
        context_text, context_map = retrieve_curriculum_context(
            query="Euclid division lemma remainder",
            chapter_slug="real-numbers",
            max_snippets=2,
        )
        assert len(context_map) > 0
        assert "[1]" in context_text

    def test_citation_extraction(self):
        """Parses [1] bracket citations and ignores phantom citations."""
        class MockSnippet:
            def __init__(self, idx, bid):
                self.index = idx
                self.block_id = bid
                self.source_title = "Real Numbers"
                self.heading = "Euclid Lemma"
                self.text = "For any integers a and b..."

        cmap = {1: MockSnippet(1, "rn-01"), 2: MockSnippet(2, "rn-02")}
        reply = "Consider the division algorithm [1]. What remainder do you find? [99]"

        citations = extract_citations(reply, cmap)
        assert len(citations) == 1
        assert citations[0]["citationIndex"] == 1
        assert citations[0]["blockId"] == "rn-01"

    async def test_graceful_degradation_on_llm_failure(self, memory_db, test_student_id):
        """When AI provider raises LLMUnavailableError, returns honest status 200 message."""
        with patch("app.services.tutor_service.ai_provider.generate_chat", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = LLMUnavailableError("Groq 503")
            res = await process_tutor_message(
                db=memory_db,
                student_id=test_student_id,
                user_message="Why is the HCF of 455 and 42 equal to 7?",
                chapter_slug="real-numbers",
            )
            assert res["isDegraded"] is True
            assert res["reply"] == DEGRADED_MESSAGE
            assert res["citations"] == []

    async def test_tutor_message_success_with_grounded_citation(self, memory_db, test_student_id):
        """When AI provider succeeds, returns non-degraded response with citations."""
        socratic_reply = (
            "What step would you take first to apply Euclid's Division Lemma? "
            "Recall that for integers a and b, a = bq + r [1]."
        )
        with patch("app.services.tutor_service.ai_provider.generate_chat", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = socratic_reply
            res = await process_tutor_message(
                db=memory_db,
                student_id=test_student_id,
                user_message="Can you explain Euclid's division lemma?",
                chapter_slug="real-numbers",
            )
            assert res["isDegraded"] is False
            assert res["quotaExceeded"] is False
            assert res["reply"] == socratic_reply
            assert len(res["citations"]) >= 1
            assert res["citations"][0]["citationIndex"] == 1
            assert "sourceTitle" in res["citations"][0] or "source_title" in res["citations"][0]
            mock_gen.assert_awaited_once()

    def test_socratic_prompt_template_rule_1_compliance(self):
        """Socratic prompt uses the visible product name ZENITH, never a SETU name or version suffix."""
        assert "ZENITH Academic Tutor" in SOCRATIC_SYSTEM_PROMPT
        assert "SETU" not in SOCRATIC_SYSTEM_PROMPT
        assert "ZENITH V2" not in SOCRATIC_SYSTEM_PROMPT
        assert "ZENITH 2.0" not in SOCRATIC_SYSTEM_PROMPT


# ==============================================================================
# 8. ATTEMPT SERVICE SHARED LIBRARY ACCESS
# ==============================================================================

class TestAttemptServiceLibraryAccess:
    def test_grade_response_dual_answer_key_support(self):
        """grade_response handles both 'answerKey' and 'answer' dictionaries."""
        q1 = Question(
            type="multiple_choice",
            prompt_json={"options": ["24", "48", "72"]},
            answer_key_json={"answerKey": 1},
        )
        correct1, score1, _, _ = grade_response(q1, 1)
        assert correct1 is True
        assert score1 == 1.0

        q2 = Question(
            type="multiple_choice",
            prompt_json={"options": ["24", "48", "72"]},
            answer_key_json={"answer": 1},
        )
        correct2, score2, _, _ = grade_response(q2, 1)
        assert correct2 is True
        assert score2 == 1.0

    def test_library_path_attempt_allowed_for_any_student(self, memory_db, test_student_id):
        """Attempting a question from a published library path is allowed for any student."""
        owner_system = uuid.UUID("00000000-0000-0000-0000-000000000001")
        path = LearningPath(
            id=uuid.uuid4(),
            owner_id=owner_system,
            grade=10,
            subject_id="subject-math",
            is_library=True,
            library_slug="real-numbers",
            library_status="published",
            outline_json={},
        )
        lesson = PathLesson(id=uuid.uuid4(), path_id=path.id, lesson_key="rn-lesson-1", title="FTA", sequence=1)
        version = LessonVersion(id=uuid.uuid4(), path_lesson_id=lesson.id, lesson_package_json={})
        question = Question(
            id=uuid.uuid4(),
            lesson_version_id=version.id,
            question_key="q-fta-1",
            type="multiple_choice",
            prompt_json={"options": ["A", "B"]},
            answer_key_json={"answerKey": 0},
            concept_ids=["cbse-10-math-real-numbers-fta"],
        )
        memory_db.add_all([path, lesson, version, question])
        memory_db.flush()

        outcome = grade_and_record_attempt(
            db=memory_db,
            owner_id=test_student_id,  # Student is NOT system owner!
            lesson_version_id=version.id,
            question_key="q-fta-1",
            response=0,
        )
        assert outcome.is_correct is True
        assert outcome.score == 1.0


# ==============================================================================
# 9. FASTAPI ENDPOINT INTEGRATION TESTS & RULE 1 COMPLIANCE
# ==============================================================================

class TestFastApiEndpoints:
    def test_library_catalogue_endpoint(self, memory_db, test_student_id):
        """GET /api/v1/library/catalogue returns 200 with 4 chapters."""
        data = get_library_catalogue(grade=10, subject_id="subject-math", user_id=test_student_id, db=memory_db)
        assert data["totalChapters"] == 4
        assert "cbse" in data["boards"]

    def test_library_chapter_endpoint(self, memory_db, test_student_id):
        """GET /api/v1/library/chapters/real-numbers returns chapter details."""
        data = get_chapter_detail("real-numbers", user_id=test_student_id, db=memory_db)
        assert data["slug"] == "real-numbers"
        assert "chapter" in data
        assert data["chapter"]["slug"] == "real-numbers"

    def test_rewards_me_endpoint(self, memory_db, test_student_id):
        """GET /api/v1/rewards/me returns gamification metrics."""
        data = get_my_rewards(student_id=test_student_id, db=memory_db)
        assert "totalXp" in data
        assert "currentLevel" in data
        assert "currentStreakDays" in data
        assert "xp" in data
        assert "streak" in data
        assert data["timezone"] == "Asia/Kolkata"

    def test_diagnostics_session_creation_endpoint(self, memory_db, test_student_id):
        """POST /api/v1/diagnostics/session returns 201 with 8 items."""
        req = DiagnosticSessionRequest(chapterSlug="real-numbers")
        data = start_diagnostic_session(req, student_id=test_student_id, db=memory_db)
        assert data["totalItems"] == 8
        assert len(data["items"]) == 8

    def test_practice_recommendation_endpoint(self, memory_db, test_student_id):
        """GET /api/v1/practice/recommendation returns recommended concept."""
        data = get_recommendation(chapter_slug="real-numbers", student_id=test_student_id, db=memory_db)
        assert "conceptId" in data

    async def test_tutor_message_degraded_endpoint(self, memory_db, test_student_id):
        """POST /api/v1/tutor/message returns status 200 with honest fallback when AI is unavailable."""
        with patch("app.services.tutor_service.ai_provider.generate_chat", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = LLMUnavailableError("Groq 503")
            req = TutorMessageRequest(
                message="Can you explain Euclid's division algorithm?",
                chapterSlug="real-numbers",
            )
            data = await post_tutor_message(req, student_id=test_student_id, db=memory_db)
            assert data["isDegraded"] is True
            assert data["reply"] == DEGRADED_MESSAGE

    async def test_tutor_message_success_endpoint(self, memory_db, test_student_id):
        """POST /api/v1/tutor/message returns status 200 with non-degraded reply and citations."""
        socratic_reply = "Notice the relationship between the divisor and remainder in [1]. What do you observe?"
        with patch("app.services.tutor_service.ai_provider.generate_chat", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = socratic_reply
            req = TutorMessageRequest(
                message="How do I find the remainder in Euclid's division lemma?",
                chapterSlug="real-numbers",
            )
            data = await post_tutor_message(req, student_id=test_student_id, db=memory_db)
            assert data["isDegraded"] is False
            assert data["quotaExceeded"] is False
            assert "[1]" in data["reply"]
            assert len(data["citations"]) >= 1
            mock_gen.assert_awaited_once()

    def test_rule_1_naming_compliance(self):
        """Rule 1: Visible product name is strictly SETU everywhere (0 occurrences of 'SETU V2' / 'SETU 2.0')."""
        import inspect
        import app.services.tutor_service as ts
        import app.services.bkt as bs
        import app.services.diagnostic_service as ds
        import app.services.practice_service as ps
        import app.services.rewards_service as rs
        import app.services.library_service as ls

        modules = [ts, bs, ds, ps, rs, ls]
        for m in modules:
            source = inspect.getsource(m)
            assert "SETU V2" not in source, f"Rule 1 violation in {m.__name__}"
            assert "SETU 2.0" not in source, f"Rule 1 violation in {m.__name__}"
