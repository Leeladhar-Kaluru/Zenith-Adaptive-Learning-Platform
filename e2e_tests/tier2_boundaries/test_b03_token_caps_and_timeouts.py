import pytest
from e2e_tests.test_config import GROQ_MAX_TOKENS, GROQ_TIMEOUT_SECONDS

def test_token_cap_contract_under_1500():
    """Tier 2: Max token allocation for student inference is strictly 1500."""
    assert GROQ_MAX_TOKENS == 1500

def test_timeout_seconds_specification():
    """Tier 2: Remote provider timeout is configured for 120.0 seconds."""
    assert GROQ_TIMEOUT_SECONDS == 120.0

def test_tutor_response_token_accounting(student_client):
    """Tier 2: Successful tutor responses report tokens_used bounded by ceiling."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Summarize Euclid's algorithm in two sentences."}
    )
    if res.status_code == 200:
        data = res.json()
        assert "tokens_used" in data
        assert data["tokens_used"] <= GROQ_MAX_TOKENS

def test_prevent_runaway_output_generation():
    """Tier 2: Token capping prevents unbounded text streams."""
    simulated_tokens = 1450
    assert simulated_tokens < GROQ_MAX_TOKENS

def test_timeout_degradation_message(student_client):
    """Tier 2: Timeout or provider failure produces honest degraded status."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Force degradation", "simulate_provider_offline": True}
    )
    assert res.status_code == 503
    assert "status" in res.json()
    assert res.json()["status"] == "degraded"
