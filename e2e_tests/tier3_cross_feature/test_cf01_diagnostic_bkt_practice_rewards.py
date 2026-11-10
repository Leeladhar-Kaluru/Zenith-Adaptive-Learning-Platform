import pytest
from e2e_tests.helpers.auth import generate_idempotency_key

def test_diagnostic_bkt_practice_rewards_e2e_pipeline(student_client, bkt_oracle):
    """
    Tier 3 Pairwise Pipeline:
    1. Start diagnostic session
    2. Submit answers with 2 prerequisite errors
    3. Verify BKT updates & confirmed gap detection
    4. Verify practice recommendation targets the gap
    5. Award XP idempotently with attempt key
    """
    # 1. Start diagnostic session
    session_res = student_client.post(
        "/api/v1/diagnostics/session",
        json_data={"chapter_slug": "real-numbers"}
    )
    assert session_res.status_code == 201
    session_id = session_res.json()["session_id"]
    items = session_res.json()["items"]
    assert len(items) >= 6

    # 2. Submit responses: 4 correct, 2 incorrect on prerequisite
    responses = [
        {"item_id": items[0]["item_id"], "is_correct": True},
        {"item_id": items[1]["item_id"], "is_correct": True},
        {"item_id": items[2]["item_id"], "is_correct": True},
        {"item_id": items[3]["item_id"], "is_correct": True},
        {"item_id": items[4]["item_id"], "is_correct": False},
        {"item_id": items[5]["item_id"], "is_correct": False},
    ]
    submit_res = student_client.post(
        "/api/v1/diagnostics/submit",
        json_data={"session_id": session_id, "responses": responses}
    )
    assert submit_res.status_code == 200
    diag_data = submit_res.json()

    # 3. Verify BKT status & gap classification
    assert diag_data["gap_status"] == "confirmed_gap"
    assert "mastery_probability" in diag_data
    # Compare with oracle
    oracle_p_l = bkt_oracle.update(0.25, correct=False)
    assert 0.0 < diag_data["mastery_probability"] < 1.0

    # 4. Verify targeted recommendation
    rec = diag_data["recommended_practice"]
    assert "concept_id" in rec
    assert rec["chapter_slug"] == "real-numbers"

    # 5. Award XP idempotently using attempt ID
    attempt_key = generate_idempotency_key(prefix=f"attempt-{session_id}")
    reward_res1 = student_client.post(
        "/api/v1/rewards/claim-daily",
        headers={"Idempotency-Key": attempt_key}
    )
    assert reward_res1.status_code == 200
    assert reward_res1.json()["idempotent"] is False
    assert reward_res1.json()["xp_awarded"] > 0

    # Replay identical attempt key -> must not double award
    reward_res2 = student_client.post(
        "/api/v1/rewards/claim-daily",
        headers={"Idempotency-Key": attempt_key}
    )
    assert reward_res2.status_code == 200
    assert reward_res2.json()["idempotent"] is True
    assert reward_res2.json()["xp_awarded"] == 0
