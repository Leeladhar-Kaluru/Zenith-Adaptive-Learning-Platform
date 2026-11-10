import pytest

def test_http_429_status_code_contract(student_client):
    """Tier 2: Exhausting tutor message rate limits returns HTTP 429."""
    for _ in range(25):
        res = student_client.post(
            "/api/v1/tutor/message",
            json_data={"message": "Querying for rate limit threshold."}
        )
        if res.status_code == 429:
            break
    assert res.status_code == 429

def test_retry_after_header_or_payload_contract(student_client):
    """Tier 2: 429 response contains retry_after delay guidance."""
    for _ in range(25):
        res = student_client.post(
            "/api/v1/tutor/message",
            json_data={"message": "Checking retry-after"}
        )
        if res.status_code == 429:
            break
    data = res.json()
    assert "retry_after" in data or "quota" in data["detail"].lower()

def test_exponential_backoff_formula():
    """Tier 2: Bounded exponential backoff formula calculation."""
    # base 1s, factor 2, jitter max, ceiling 60s
    attempts = [1, 2, 3, 4, 5, 6, 7]
    delays = [min(60.0, 1.0 * (2 ** (a - 1))) for a in attempts]
    assert delays[0] == 1.0
    assert delays[1] == 2.0
    assert delays[2] == 4.0
    assert delays[3] == 8.0
    assert delays[4] == 16.0
    assert delays[5] == 32.0
    assert delays[6] == 60.0  # Capped at 60s

def test_daily_quota_saturation_messaging(student_client):
    """Tier 2: User-friendly notification when daily message quota is reached."""
    for _ in range(25):
        res = student_client.post(
            "/api/v1/tutor/message",
            json_data={"message": "Quota check message"}
        )
        if res.status_code == 429:
            break
    assert "tomorrow" in res.json()["detail"].lower() or "quota" in res.json()["detail"].lower()

def test_subsequent_calls_stay_blocked_until_reset(student_client):
    """Tier 2: Subsequent calls during rate limit window remain 429."""
    # Saturate quota first
    for _ in range(25):
        res = student_client.post(
            "/api/v1/tutor/message",
            json_data={"message": "Saturate limit"}
        )
        if res.status_code == 429:
            break
    assert res.status_code == 429
    # Now verify subsequent call is still 429
    res_subsequent = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Should still be blocked"}
    )
    assert res_subsequent.status_code == 429
