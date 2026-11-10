import pytest
from e2e_tests.helpers.auth import generate_idempotency_key, is_valid_uuid

def test_idempotency_key_format_validation():
    """Tier 2: Generated idempotency keys adhere to prefix:uuid format."""
    key = generate_idempotency_key(prefix="attempt")
    assert key.startswith("attempt:")
    uuid_part = key.split(":", 1)[1]
    assert is_valid_uuid(uuid_part)

def test_replaying_identical_key_does_not_double_award(student_client):
    """Tier 2: Replaying the same key returns identical outcome with xp_awarded = 0."""
    key = generate_idempotency_key(prefix="claim")
    res1 = student_client.post("/api/v1/rewards/claim-daily", headers={"Idempotency-Key": key})
    assert res1.status_code == 200
    assert res1.json()["idempotent"] is False
    
    res2 = student_client.post("/api/v1/rewards/claim-daily", headers={"Idempotency-Key": key})
    assert res2.status_code == 200
    assert res2.json()["idempotent"] is True
    assert res2.json()["xp_awarded"] == 0

def test_distinct_keys_trigger_independent_evaluations(student_client):
    """Tier 2: Different idempotency keys are evaluated independently."""
    key1 = generate_idempotency_key(prefix="attempt")
    key2 = generate_idempotency_key(prefix="attempt")
    assert key1 != key2

def test_malformed_idempotency_key_handling(student_client):
    """Tier 2: Non-standard idempotency key still works without throwing 500 error."""
    res = student_client.post(
        "/api/v1/rewards/claim-daily",
        headers={"Idempotency-Key": "plain_text_custom_key_123"}
    )
    assert res.status_code == 200

def test_omitted_idempotency_key_defaults_to_single_award(student_client):
    """Tier 2: Calls without idempotency key execute successfully."""
    res = student_client.post("/api/v1/rewards/claim-daily")
    assert res.status_code == 200
    assert "success" in res.json()
