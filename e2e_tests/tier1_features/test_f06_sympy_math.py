import pytest

def test_euclid_division_lemma_correctness(math_verifier):
    """Feature 6: Mathematical verification of Euclid's Division Lemma a = bq + r."""
    # 45 = 6 * 7 + 3
    assert math_verifier.verify_euclid_division(a=45, b=6, q=7, r=3) is True
    # Invalid: remainder >= divisor (45 = 6 * 6 + 9)
    assert math_verifier.verify_euclid_division(a=45, b=6, q=6, r=9) is False

def test_fundamental_theorem_hcf_lcm(math_verifier):
    """Feature 6: Verification of HCF(a, b) * LCM(a, b) == a * b."""
    # For numbers 12 and 18: HCF is 6, LCM is 36. 6 * 36 = 216 == 12 * 18
    assert math_verifier.verify_hcf_lcm_identity(12, 18, 6, 36) is True
    # Invariant: 96 and 404
    hcf_96_404 = 4
    lcm_96_404 = 9696
    assert math_verifier.verify_hcf_lcm_identity(96, 404, hcf_96_404, lcm_96_404) is True

def test_quadratic_roots_discriminant_positive(math_verifier):
    """Feature 6: Solves quadratic roots when discriminant > 0."""
    # x^2 - 5x + 6 = 0 -> roots are 2 and 3
    r1, r2, disc = math_verifier.solve_quadratic_roots(1, -5, 6)
    assert disc == 1.0
    assert r1 == 2.0
    assert r2 == 3.0

def test_quadratic_roots_discriminant_zero(math_verifier):
    """Feature 6: Solves quadratic roots when discriminant == 0."""
    # x^2 - 4x + 4 = 0 -> root is 2 (repeated)
    r1, r2, disc = math_verifier.solve_quadratic_roots(1, -4, 4)
    assert disc == 0.0
    assert r1 == 2.0
    assert r2 == 2.0

def test_linear_system_classification(math_verifier):
    """Feature 6: Classifies consistency and solutions for pairs of linear equations."""
    # Intersecting lines (unique solution): 2x + 3y - 7 = 0 and 3x + 4y - 10 = 0
    res = math_verifier.classify_linear_system(2, 3, -7, 3, 4, -10)
    assert res == "unique"

    # Parallel lines (no solution): 2x + 4y - 8 = 0 and x + 2y - 3 = 0
    res_par = math_verifier.classify_linear_system(2, 4, -8, 1, 2, -3)
    assert res_par == "parallel"
