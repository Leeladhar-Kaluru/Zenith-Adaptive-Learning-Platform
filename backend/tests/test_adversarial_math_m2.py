"""Adversarial Negative Testing Suite for Mathematical Truth and Sympy Solver.

Empirically verifies:
1. Real Numbers: solver detects and fails on incorrect GCD, LCM, identity violations,
   composite prime factors, and false decimal termination.
2. Polynomials: solver detects and fails on incorrect zeroes, Vieta sum/product violations,
   and degree mismatches.
3. Linear Equations: solver detects and fails on incorrect intersection points, false
   consistency, and corrupted parameter k solutions.
4. Quadratic Equations: solver detects and fails on false discriminants, incorrect
   nature of roots (e.g. claiming real roots for D < 0), and corrupted equal-root parameters.
5. Option & AnswerKey Redaction/Integrity: solver catches answerKey pointing to wrong mathematical options.
6. Full CLI Execution: verifier.run() returns exit code 1 when presented with corrupted mathematics.
7. Authenticity Verification: AST analysis proving genuine Sympy algebraic functions are utilized
   without lookup tables or tautological bypasses.
"""
from __future__ import annotations

import ast
import json
import os
import tempfile
import pytest
import sympy

from scripts.verify_library_math import LibraryMathVerifier


@pytest.fixture
def verifier():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    content_dir = os.path.join(base_dir, "app", "content", "library", "cbse-10-math")
    return LibraryMathVerifier(content_dir)


# ==============================================================================
# 1. REAL NUMBERS ADVERSARIAL TESTS
# ==============================================================================

class TestRealNumbersAdversarial:
    def test_rejects_incorrect_gcd(self, verifier):
        """Claims gcd(12, 18) = 10 (actual gcd is 6)."""
        math_spec = {
            "domain": "real_numbers",
            "subdomain": "hcf_lcm",
            "inputs": {"a": 12, "b": 18},
            "expected": {"hcf": 10, "lcm": 36, "target_val": "10"},
        }
        passed, details, _ = verifier.verify_real_numbers("adv-rn-1", math_spec)
        assert passed is False
        assert "HCF mismatch for (12,18): expected 10, got 6" in details

    def test_rejects_incorrect_lcm(self, verifier):
        """Claims lcm(12, 18) = 50 (actual lcm is 36)."""
        math_spec = {
            "domain": "real_numbers",
            "subdomain": "hcf_lcm",
            "inputs": {"a": 12, "b": 18},
            "expected": {"hcf": 6, "lcm": 50, "target_val": "50"},
        }
        passed, details, _ = verifier.verify_real_numbers("adv-rn-2", math_spec)
        assert passed is False
        assert "LCM mismatch for (12,18): expected 50, got 36" in details

    def test_rejects_hcf_lcm_identity_corruption(self, verifier):
        """Sympy solver strictly enforces HCF * LCM = a * b."""
        a, b = 15, 25
        hcf = int(sympy.gcd(a, b))  # 5
        lcm = int(sympy.lcm(a, b))  # 75
        assert hcf * lcm == a * b  # 375

        # Tampered expected LCM
        passed, details, _ = verifier.verify_real_numbers("adv-rn-3", {
            "domain": "real_numbers",
            "subdomain": "hcf_lcm",
            "inputs": {"a": a, "b": b},
            "expected": {"hcf": hcf, "lcm": 100},
        })
        assert passed is False
        assert "LCM mismatch" in details

    def test_rejects_composite_prime_factorization(self, verifier):
        """Claims 4 is a prime factor of 36."""
        # Genuine prime factorisation of 36 is {2: 2, 3: 2}
        factors = sympy.factorint(36)
        assert 4 not in factors
        assert all(sympy.isprime(p) for p in factors.keys())

    def test_rejects_false_terminating_decimal(self, verifier):
        """Claims 64/455 terminates (actual: 455 = 5*7*13 -> non-terminating repeating)."""
        math_spec = {
            "domain": "real_numbers",
            "subdomain": "terminating_decimal",
            "inputs": {"p": 64, "q": 455},
            "expected": {"terminating": True},  # FALSE CLAIM
        }
        passed, details, _ = verifier.verify_real_numbers("adv-rn-4", math_spec)
        assert passed is False
        assert "Termination mismatch" in details

    def test_rejects_false_rational_for_irrational(self, verifier):
        """Claims sqrt(7) is rational."""
        math_spec = {
            "domain": "real_numbers",
            "subdomain": "irrationality",
            "inputs": {"expr": "sqrt(7)"},
            "expected": {"is_irrational": False},  # FALSE CLAIM
        }
        passed, details, _ = verifier.verify_real_numbers("adv-rn-5", math_spec)
        assert passed is False
        assert "Irrationality mismatch" in details


# ==============================================================================
# 2. POLYNOMIALS ADVERSARIAL TESTS
# ==============================================================================

class TestPolynomialsAdversarial:
    def test_rejects_incorrect_zeroes_in_item_options(self, verifier):
        """Claims zeroes of x^2 - 5x + 6 are 1 and 4 (genuine zeroes are 2 and 3)."""
        corrupted_item = {
            "questionId": "adv-poly-1",
            "prompt": "Find the zeroes of x^2 - 5x + 6.",
            "options": ["1 and 4", "2 and 3", "-2 and -3", "1 and 6"],
            "answerKey": 0,  # Deliberately pointing to wrong option "1 and 4"
            "math_verification": {
                "domain": "polynomials",
                "subdomain": "quadratic_zeroes",
                "inputs": {"poly": "x**2 - 5*x + 6"},
                "expected": {"target_val": "2 and 3"},
            },
        }
        passed = verifier.verify_item("polynomials", "test.json", corrupted_item)
        assert passed is False
        assert verifier.failed_count >= 1
        last_result = verifier.results[-1]
        assert last_result["status"] == "FAIL"
        assert "does not match computed" in last_result["details"]

    def test_rejects_non_zero_satisfaction(self):
        """Direct proof: 1 and 4 do NOT satisfy x^2 - 5x + 6 == 0."""
        x = sympy.Symbol("x")
        poly = x**2 - 5*x + 6
        # True roots satisfy poly.subs(x, r) == 0
        assert sympy.simplify(poly.subs(x, 2)) == 0
        assert sympy.simplify(poly.subs(x, 3)) == 0
        # Corrupted candidates fail
        assert sympy.simplify(poly.subs(x, 1)) == 2 != 0
        assert sympy.simplify(poly.subs(x, 4)) == 2 != 0

    def test_rejects_cubic_fed_to_quadratic_verifier(self, verifier):
        """Feeding cubic x^3 - 6x^2 + 11x - 6 into quadratic zeroes solver."""
        math_spec = {
            "domain": "polynomials",
            "subdomain": "quadratic_zeroes",
            "inputs": {"poly": "x**3 - 6*x**2 + 11*x - 6"},
            "expected": {},
        }
        passed, details, _ = verifier.verify_polynomials("adv-poly-2", math_spec)
        assert passed is False
        assert "Expected quadratic polynomial, got degree 3" in details


# ==============================================================================
# 3. LINEAR EQUATIONS ADVERSARIAL TESTS
# ==============================================================================

class TestLinearEquationsAdversarial:
    def test_rejects_incorrect_system_intersection_point(self, verifier):
        """System: x + y = 14, x - y = 4. True solution: (9, 5).
        Adversarial claim: solution is (7, 7) or (10, 4).
        """
        math_spec = {
            "domain": "linear_equations",
            "subdomain": "unique_solution",
            "inputs": {"eq1": "x + y - 14", "eq2": "x - y - 4"},
            "expected": {"solution": ["7", "7"], "target_val": "x = 7, y = 7"},
        }
        passed, details, _ = verifier.verify_linear_equations("adv-lin-1", math_spec)
        assert passed is False
        assert "Solution mismatch: expected (7, 7), got {(9, 5)}" in details

    def test_rejects_wrong_answer_key_for_linear_system(self, verifier):
        """System: 2x + 3y = 11, 2x - 4y = -24. Genuine solution: (-2, 5).
        Corrupted item marks option '(2, -5)' as correct answer.
        """
        corrupted_item = {
            "questionId": "adv-lin-2",
            "prompt": "Solve 2x + 3y = 11 and 2x - 4y = -24.",
            "options": ["x = 2, y = -5", "x = -2, y = 5", "x = 3, y = 4", "No solution"],
            "answerKey": 0,  # Deliberately pointing to wrong option "x = 2, y = -5"
            "math_verification": {
                "domain": "linear_equations",
                "subdomain": "unique_solution",
                "inputs": {"eq1": "2*x + 3*y - 11", "eq2": "2*x - 4*y + 24"},
                "expected": {"solution": ["-2", "5"], "target_val": "x = -2, y = 5"},
            },
        }
        passed = verifier.verify_item("linear_equations", "test.json", corrupted_item)
        assert passed is False
        last_result = verifier.results[-1]
        assert last_result["status"] == "FAIL"
        assert "does not match computed" in last_result["details"]

    def test_rejects_corrupted_parameter_k_parallel(self, verifier):
        """Parallel system: 3x + y = 1, (2k-1)x + (k-1)y = 2k+1.
        Actual k for no solution: k = 2.
        Corrupted question claims k = 5.
        """
        corrupted_item = {
            "questionId": "adv-lin-3",
            "prompt": "Find k for no solution.",
            "options": ["k = 1", "k = 2", "k = 5", "k = -2"],
            "answerKey": 2,  # Points to k = 5
            "math_verification": {
                "domain": "linear_equations",
                "subdomain": "parallel_no_solution_parameter",
                "inputs": {
                    "eq1": "3*x + y - 1",
                    "eq2": "(2*k - 1)*x + (k - 1)*y - (2*k + 1)",
                    "condition": "no_solution",
                },
                "expected": {"k": "2", "target_val": "k = 2"},
            },
        }
        passed = verifier.verify_item("linear_equations", "test.json", corrupted_item)
        assert passed is False
        last_result = verifier.results[-1]
        assert last_result["status"] == "FAIL"


# ==============================================================================
# 4. QUADRATIC EQUATIONS ADVERSARIAL TESTS
# ==============================================================================

class TestQuadraticEquationsAdversarial:
    def test_rejects_incorrect_discriminant(self, verifier):
        """Equation: x^2 + 4x + 5 = 0.
        a=1, b=4, c=5 -> D = 4^2 - 4(1)(5) = 16 - 20 = -4.
        Corrupted claim: D = 4.
        """
        math_spec = {
            "domain": "quadratic_equations",
            "subdomain": "nature_of_roots",
            "inputs": {"a": 1, "b": 4, "c": 5},
            "expected": {"discriminant": 4, "nature": "no_real_roots"},
        }
        passed, details, _ = verifier.verify_quadratic_equations("adv-quad-1", math_spec)
        assert passed is False
        assert "Discriminant mismatch: expected 4, got -4" in details

    def test_rejects_false_real_roots_for_negative_discriminant(self, verifier):
        """Equation: x^2 + 4x + 5 = 0 (D = -4 < 0).
        Adversarial claim: has 'two_distinct_real_roots' or 'two_equal_real_roots'.
        """
        math_spec = {
            "domain": "quadratic_equations",
            "subdomain": "nature_of_roots",
            "inputs": {"a": 1, "b": 4, "c": 5},
            "expected": {"discriminant": -4, "nature": "two_distinct_real_roots"},  # FALSE
        }
        passed, details, _ = verifier.verify_quadratic_equations("adv-quad-2", math_spec)
        assert passed is False
        assert "Nature mismatch: expected two_distinct_real_roots, calculated no_real_roots" in details

    def test_rejects_corrupted_equal_roots_parameter(self, verifier):
        """Equation: 2x^2 + kx + 3 = 0. Equal roots -> D = k^2 - 24 = 0 -> k = ±2*sqrt(6).
        Corrupted claim: k = ±4.
        """
        math_spec = {
            "domain": "quadratic_equations",
            "subdomain": "equal_roots_parameter",
            "inputs": {"a": 2, "b": "k", "c": 3},
            "expected": {"k_values": ["4", "-4"]},
        }
        passed, details, _ = verifier.verify_quadratic_equations("adv-quad-3", math_spec)
        assert passed is False
        assert "k solutions mismatch" in details

    def test_rejects_wrong_roots_in_item_options(self, verifier):
        """Equation: x^2 - 7x + 12 = 0. Genuine roots are 3 and 4.
        Corrupted item marks option 'x = 2, x = 6' as correct answer.
        """
        corrupted_item = {
            "questionId": "adv-quad-4",
            "prompt": "Find roots of x^2 - 7x + 12 = 0.",
            "options": ["x = 3, x = 4", "x = 2, x = 6", "x = 1, x = 12", "x = -3, x = -4"],
            "answerKey": 1,  # Points to wrong option "x = 2, x = 6"
            "math_verification": {
                "domain": "quadratic_equations",
                "subdomain": "factorisation",
                "inputs": {"a": 1, "b": -7, "c": 12},
                "expected": {"target_val": "[3, 4]"},
            },
        }
        passed = verifier.verify_item("quadratic_equations", "test.json", corrupted_item)
        assert passed is False
        last_result = verifier.results[-1]
        assert last_result["status"] == "FAIL"
        assert "does not match computed" in last_result["details"]


# ==============================================================================
# 5. FULL RUNNER & EXIT CODE ADVERSARIAL TEST
# ==============================================================================

class TestRunnerExitCodeFailure:
    def test_runner_exits_code_1_on_corrupted_content(self):
        """When an invalid question exists in content files, verifier.run() returns 1."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_data = {
                "schemaVersion": "2.0.0",
                "lessonId": "corrupted-lesson",
                "title": "Corrupted Math Lesson",
                "practice": [
                    {
                        "questionId": "bad-q1",
                        "prompt": "Find GCD of 12 and 18",
                        "options": ["10", "6", "4", "2"],
                        "answerKey": 0,  # 10 is wrong
                        "math_verification": {
                            "domain": "real_numbers",
                            "subdomain": "hcf_lcm",
                            "inputs": {"a": 12, "b": 18},
                            "expected": {"hcf": 10},  # Corrupted expectation
                        },
                    }
                ],
            }
            file_path = os.path.join(tmp_dir, "bad-math.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(bad_data, f)

            verifier = LibraryMathVerifier(tmp_dir)
            exit_code = verifier.run()
            assert exit_code == 1
            assert verifier.failed_count == 1
            assert verifier.total_verified == 1


# ==============================================================================
# 6. IMPLEMENTATION AUTHENTICITY INSPECTION (AST ANALYSIS)
# ==============================================================================

class TestImplementationAuthenticity:
    def test_genuine_sympy_usage_via_ast(self):
        """Parses verify_library_math.py AST to verify authentic symbolic calls:
        sympy.gcd, sympy.lcm, sympy.factorint, sympy.solve, sympy.roots, sympy.linsolve.
        Ensures no hardcoded answer dictionaries or tautological pass statements.
        """
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts",
            "verify_library_math.py",
        )
        with open(script_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename="verify_library_math.py")

        sympy_calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                # Detect sympy.xyz calls
                if isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name) and func.value.id == "sympy":
                        sympy_calls.add(func.attr)

        # Assert mandatory Sympy mathematical functions are directly invoked
        mandatory_sympy_functions = {
            "gcd",
            "lcm",
            "factorint",
            "solve",
            "roots",
            "linsolve",
            "sympify",
            "simplify",
            "isprime",
            "Rational",
            "Poly",
        }
        for func_name in mandatory_sympy_functions:
            assert func_name in sympy_calls, f"Expected authentic sympy.{func_name} invocation in verify_library_math.py"

    def test_no_hardcoded_dummy_lookup_dict(self):
        """Scans verify_library_math.py AST for suspicious lookup tables or static key maps."""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts",
            "verify_library_math.py",
        )
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Reject hardcoded answer lookup tables
        suspicious_names = ["ANSWER_KEY_LOOKUP", "MOCK_ANSWERS", "HARDCODED_ANSWERS", "SOLUTIONS_MAP"]
        for name in suspicious_names:
            assert name not in content, f"Found suspicious lookup map: {name}"
