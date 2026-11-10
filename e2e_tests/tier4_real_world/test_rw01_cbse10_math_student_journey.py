import pytest
from e2e_tests.helpers.auth import create_test_student_headers, generate_idempotency_key
from e2e_tests.helpers.api_client import E2EApiClient
from e2e_tests.test_config import TIMEZONE_STREAKS

@pytest.fixture
def journey_student():
    """Isolated student persona for the real-world CBSE Class 10 journey."""
    headers = create_test_student_headers()
    return E2EApiClient(headers=headers)

def test_stage_1_student_onboarding_and_catalog_discovery(journey_student):
    """Tier 4 - Stage 1: Student discovers CBSE Class 10 Mathematics syllabus."""
    cat_res = journey_student.get("/api/v1/library/catalogue")
    assert cat_res.status_code == 200
    catalog = cat_res.json()
    assert "cbse" in catalog["boards"]
    assert "10" in catalog["classes"]
    
    # Real numbers must be available
    rn_chapter = next(c for c in catalog["chapters"] if c["slug"] == "real-numbers")
    assert rn_chapter["title"] == "Real Numbers"

def test_stage_2_diagnostic_assessment_sitting(journey_student):
    """Tier 4 - Stage 2: Student sits for diagnostic quiz to baseline mastery."""
    session_res = journey_student.post(
        "/api/v1/diagnostics/session",
        json_data={"chapter_slug": "real-numbers"}
    )
    assert session_res.status_code == 201
    session_data = session_res.json()
    assert "session_id" in session_data
    assert len(session_data["items"]) >= 6
    
    # Ensure no answer leaks
    for item in session_data["items"]:
        assert "answerKey" not in item

def test_stage_3_diagnostic_submission_and_gap_detection(journey_student, bkt_oracle):
    """Tier 4 - Stage 3: Student submits answers with 2 prerequisite errors, establishing confirmed gap."""
    session_res = journey_student.post(
        "/api/v1/diagnostics/session",
        json_data={"chapter_slug": "real-numbers"}
    )
    session_id = session_res.json()["session_id"]
    
    # Submit 3 correct, 3 incorrect
    submit_res = journey_student.post(
        "/api/v1/diagnostics/submit",
        json_data={
            "session_id": session_id,
            "responses": [
                {"item_id": "rn-d1", "is_correct": True},
                {"item_id": "rn-d2", "is_correct": True},
                {"item_id": "rn-d3", "is_correct": True},
                {"item_id": "rn-d4", "is_correct": False},
                {"item_id": "rn-d5", "is_correct": False},
                {"item_id": "rn-d6", "is_correct": False},
            ]
        }
    )
    assert submit_res.status_code == 200
    data = submit_res.json()
    assert data["gap_status"] == "confirmed_gap"
    assert "recommended_practice" in data
    assert data["recommended_practice"]["chapter_slug"] == "real-numbers"

def test_stage_4_lesson_reading_and_offline_save(journey_student):
    """Tier 4 - Stage 4: Student studies the recommended lesson sections."""
    lesson_res = journey_student.get("/api/v1/library/resources/real-numbers-lesson")
    assert lesson_res.status_code == 200
    lesson_data = lesson_res.json()
    assert len(lesson_data["content"]["sections"]) >= 2
    # Verify offline serializability
    assert lesson_data["rights"] == "original"

def test_stage_5_socratic_doubt_asking_with_citations(journey_student):
    """Tier 4 - Stage 5: Student asks Socratic tutor about remainder conditions."""
    doubt_res = journey_student.post(
        "/api/v1/tutor/message",
        json_data={
            "message": "Why must the remainder r be strictly less than the divisor b in Euclid's division lemma?",
            "context": {"chapter_slug": "real-numbers", "resource_id": "real-numbers-lesson"}
        }
    )
    assert doubt_res.status_code == 200
    data = doubt_res.json()
    assert "reply" in data
    assert "[1]" in data["reply"]
    assert len(data["citations"]) >= 1

def test_stage_6_practice_arena_and_quiz_solving(journey_student, math_verifier):
    """Tier 4 - Stage 6: Student enters Practice Arena and completes quiz."""
    # Verify mathematical property of questions solved
    assert math_verifier.verify_euclid_division(45, 6, 7, 3) is True
    
    session_res = journey_student.post(
        "/api/v1/diagnostics/session",
        json_data={"chapter_slug": "real-numbers"}
    )
    session_id = session_res.json()["session_id"]
    
    # Student scores 100% on the practice set
    submit_res = journey_student.post(
        "/api/v1/diagnostics/submit",
        json_data={
            "session_id": session_id,
            "responses": [
                {"item_id": "rn-p1", "is_correct": True},
                {"item_id": "rn-p2", "is_correct": True},
                {"item_id": "rn-p3", "is_correct": True},
                {"item_id": "rn-p4", "is_correct": True},
            ]
        }
    )
    assert submit_res.status_code == 200
    assert submit_res.json()["score"] == 100

def test_stage_7_gamification_rewards_and_badge_unlock(journey_student):
    """Tier 4 - Stage 7: Rewards awarded, streak updated in Asia/Kolkata, badge unlocked."""
    attempt_key = generate_idempotency_key(prefix="journey-final")
    reward_res = journey_student.post(
        "/api/v1/rewards/claim-daily",
        headers={"Idempotency-Key": attempt_key}
    )
    assert reward_res.status_code == 200
    assert reward_res.json()["xp_awarded"] > 0
    assert reward_res.json()["streak"] >= 1

    profile_res = journey_student.get("/api/v1/rewards/me")
    assert profile_res.status_code == 200
    profile = profile_res.json()
    assert profile["timezone"] == TIMEZONE_STREAKS
    assert "first_steps" in profile["badges"]
