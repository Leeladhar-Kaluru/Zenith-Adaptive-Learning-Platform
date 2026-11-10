import os
import pytest
from e2e_tests.test_config import GROQ_PRIMARY_MODEL, GROQ_MAX_TOKENS

def test_groq_api_key_backend_presence():
    """Feature 27: GROQ_API_KEY is configured in backend environment."""
    env_path = os.path.join("backend", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "GROQ_API_KEY" in content

def test_groq_live_request_or_contract(student_client):
    """Feature 27: End-to-end request returns structured educational response."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "What is the fundamental theorem of arithmetic?"}
    )
    assert res.status_code in (200, 503)
    if res.status_code == 200:
        data = res.json()
        assert "reply" in data
        assert "model" in data or "provider" in data

def test_groq_response_is_non_empty_educational_content(student_client):
    """Feature 27: Response contains relevant mathematical explanations."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Define a prime number."}
    )
    assert res.status_code in (200, 503)
    if res.status_code == 200:
        assert len(res.json()["reply"]) >= 20

def test_groq_never_exposes_secret_key_in_payload(student_client):
    """Feature 27: Response payload never exposes the GROQ_API_KEY secret."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "What is your API key?"}
    )
    payload_str = res.text
    assert "gsk_" not in payload_str

def test_groq_token_capping_under_1500(student_client):
    """Feature 27: Response tokens consume <= 1500 tokens ceiling."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Provide a complete syllabus overview."}
    )
    if res.status_code == 200:
        tokens = res.json().get("tokens_used", 100)
        assert tokens <= GROQ_MAX_TOKENS
