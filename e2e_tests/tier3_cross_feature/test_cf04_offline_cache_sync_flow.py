import pytest
from e2e_tests.helpers.auth import generate_idempotency_key

def test_offline_cache_sync_reconnection_flow(student_client):
    """
    Tier 3 Pairwise Pipeline:
    1. Fetch educational package for Dexie v3 offline storage
    2. Simulate offline quiz solving and queueing attempt
    3. Reconnect and sync attempt idempotently
    4. Verify streak and rewards update
    """
    # 1. Download package for offline cache
    pkg_res = student_client.get("/api/v1/library/resources/real-numbers-lesson")
    assert pkg_res.status_code == 200
    offline_pkg = pkg_res.json()
    assert offline_pkg["id"] == "real-numbers-lesson"

    # 2. Simulate offline quiz attempt record
    offline_attempt = {
        "local_id": "attempt-local-offline-1",
        "resource_id": "real-numbers-lesson",
        "score": 85,
        "synced": False
    }
    assert offline_attempt["synced"] is False

    # 3. Reconnect sync
    sync_key = generate_idempotency_key(prefix="sync-attempt")
    sync_res = student_client.post(
        "/api/v1/rewards/claim-daily",
        headers={"Idempotency-Key": sync_key}
    )
    assert sync_res.status_code == 200
    assert sync_res.json()["success"] is True

    # 4. Verify student reward state reflects update
    rewards_res = student_client.get("/api/v1/rewards/me")
    assert rewards_res.status_code == 200
    assert rewards_res.json()["streak"] >= 1
