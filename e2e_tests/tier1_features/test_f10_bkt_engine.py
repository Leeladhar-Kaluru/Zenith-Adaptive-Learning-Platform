import pytest

def test_bkt_correct_response_increases_mastery(bkt_oracle):
    """Feature 10: Correct answer strictly increases knowledge probability."""
    prior = 0.25
    updated = bkt_oracle.update(prior, correct=True)
    assert updated > prior, f"Expected {updated} > {prior}"

def test_bkt_incorrect_response_decreases_mastery(bkt_oracle):
    """Feature 10: Incorrect answer decreases knowledge probability before transition."""
    prior = 0.70
    updated = bkt_oracle.update(prior, correct=False)
    assert updated < prior, f"Expected {updated} < {prior}"

def test_bkt_convergence_towards_unity(bkt_oracle):
    """Feature 10: A sequence of 5 correct answers drives mastery above 0.85."""
    history = bkt_oracle.sequence_update(initial_p_l=0.25, observations=[True, True, True, True, True])
    final_mastery = history[-1]
    assert final_mastery >= 0.85
    # Strict monotonic increase
    for i in range(len(history) - 1):
        assert history[i + 1] > history[i]

def test_bkt_canonical_parameters(bkt_oracle):
    """Feature 10: BKT canonical parameter verification."""
    assert bkt_oracle.p_l0 == 0.25
    assert bkt_oracle.p_t == 0.15
    assert bkt_oracle.p_g == 0.20
    assert bkt_oracle.p_s == 0.10

def test_prerequisite_gap_classification_threshold(bkt_oracle):
    """Feature 10: 2+ errors classify as confirmed_gap; 1 error is early_signal."""
    # 2 errors -> confirmed gap
    assert bkt_oracle.classify_gap_status(errors_count=2, current_p_l=0.20) == "confirmed_gap"
    # 1 error -> early signal
    assert bkt_oracle.classify_gap_status(errors_count=1, current_p_l=0.35) == "early_signal"
    # 0 errors with high mastery -> mastered
    assert bkt_oracle.classify_gap_status(errors_count=0, current_p_l=0.90) == "mastered"
    # 0 errors with low mastery -> in progress
    assert bkt_oracle.classify_gap_status(errors_count=0, current_p_l=0.40) == "in_progress"
