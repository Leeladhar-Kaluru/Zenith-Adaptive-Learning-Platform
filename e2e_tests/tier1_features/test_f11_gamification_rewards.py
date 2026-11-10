import pytest
from e2e_tests.test_config import TIMEZONE_STREAKS, CORE_BADGES
from e2e_tests.helpers.auth import generate_idempotency_key

def test_rewards_me_returns_student_state(student_client):
    """Feature 11: GET /api/v1/rewards/me returns student's XP, coins, streak, and badges."""
    res = student_client.get("/api/v1/rewards/me")
    assert res.status_code == 200
    data = res.json()
    assert "xp" in data
    assert "coins" in data
    assert "streak" in data
    assert "badges" in data
    assert isinstance(data["xp"], int)

def test_daily_claim_awards_xp_and_streak(student_client):
    """Feature 11: Claiming daily challenge awards XP and increments streak."""
    idempotency_key = generate_idempotency_key(prefix="daily")
    res = student_client.post(
        "/api/v1/rewards/claim-daily",
        headers={"Idempotency-Key": idempotency_key}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["xp_awarded"] > 0
    assert data["streak"] >= 1

def test_idempotent_reward_issuance(student_client):
    """Feature 11: Replaying identical idempotency key yields idempotent response without duplicate reward."""
    idempotency_key = generate_idempotency_key(prefix="attempt")
    res1 = student_client.post(
        "/api/v1/rewards/claim-daily",
        headers={"Idempotency-Key": idempotency_key}
    )
    assert res1.status_code == 200
    assert res1.json()["idempotent"] is False

    # Second call with identical key
    res2 = student_client.post(
        "/api/v1/rewards/claim-daily",
        headers={"Idempotency-Key": idempotency_key}
    )
    assert res2.status_code == 200
    assert res2.json()["idempotent"] is True
    assert res2.json()["xp_awarded"] == 0

def test_asia_kolkata_timezone_contract(student_client):
    """Feature 11: Student rewards are tied to Asia/Kolkata timezone."""
    res = student_client.get("/api/v1/rewards/me")
    assert res.status_code == 200
    data = res.json()
    assert data.get("timezone") == TIMEZONE_STREAKS

def test_core_badges_catalog(client):
    """Feature 11: GET /api/v1/rewards/badges lists all 6 core badges."""
    res = client.get("/api/v1/rewards/badges")
    assert res.status_code == 200
    badges = res.json()["badges"]
    assert len(badges) >= 6
    badge_ids = [b["id"] for b in badges]
    assert "first_steps" in badge_ids
    assert "concept_master" in badge_ids
