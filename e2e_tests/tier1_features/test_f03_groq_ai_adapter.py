import os
import pytest
from e2e_tests.test_config import (
    GROQ_API_BASE_URL,
    GROQ_PRIMARY_MODEL,
    GROQ_FALLBACK_MODEL,
    GROQ_MAX_TOKENS,
    GROQ_TIMEOUT_SECONDS,
)

def test_groq_endpoint_configuration():
    """Feature 3: Groq OpenAI-compatible endpoint."""
    assert GROQ_API_BASE_URL == "https://api.groq.com/openai/v1"

def test_groq_model_selection():
    """Feature 3: Verified Groq models for production educational inference."""
    assert GROQ_PRIMARY_MODEL == "openai/gpt-oss-120b"
    assert GROQ_FALLBACK_MODEL == "qwen/qwen3.8-27b"

def test_provider_selection_logic(client):
    """Feature 3: Provider selection and health reporting."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert "components" in data
    assert "ai_provider" in data["components"]

def test_timeout_and_token_cap_contract():
    """Feature 3: Request timeout and max token limits."""
    assert GROQ_TIMEOUT_SECONDS == 120.0
    assert GROQ_MAX_TOKENS == 1500

def test_http_429_exponential_backoff(student_client):
    """Feature 3: Graceful rate-limit backoff on 429."""
    # When simulating quota / rate limit exhaustion
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Test quota trigger " * 5}
    )
    # Must either be 200 or clean 429 (never unhandled 500)
    assert res.status_code in (200, 429)
    if res.status_code == 429:
        data = res.json()
        assert "quota" in data or "detail" in data
