"""Comprehensive Unit and Integration Test Suite for Milestone 2:
Curriculum Content Engine, Math Packages, Validator, Redaction, and Seeder.

Tests:
1. Library Validator: Manifest schema, Kahn's DAG acyclicity, cycle path detection,
   concept referential integrity, Rule 6/10 rights, 20 package schemas, 4 diagnostic banks.
2. Package Redaction Service: Student payload redaction stripping answer keys, solutions,
   explanations, and steps from quiz items while strictly preserving worked examples and blocks.
3. Sympy Mathematical Solver: Formal symbolic proofs of roots, HCF/LCM, determinants,
   and discriminants across 100% of curriculum quiz items.
4. Library Seeder: Validate-only CLI execution, manifest hashing, and idempotent ingestion logic.
"""
from __future__ import annotations

import copy
import json
import os
import uuid
import pytest
import sympy

from app.services.library_validator import LibraryValidator, ValidationReport
from app.services.package_redaction import (
    redact_question_package_for_student,
    redact_single_question_for_student,
    redact_resource_package,
    redact_diagnostic_bank,
)
from app.services.library_seed import LibrarySeeder, SYSTEM_OWNER_ID
from scripts.verify_library_math import LibraryMathVerifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content", "library", "cbse-10-math")
MANIFEST_PATH = os.path.join(CONTENT_DIR, "manifest.json")


# ==============================================================================
# 1. LIBRARY VALIDATOR & DAG ACYCLICITY TESTS
# ==============================================================================

class TestLibraryValidator:
    @pytest.fixture
    def validator(self):
        return LibraryValidator()

    @pytest.fixture
    def manifest_data(self):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_manifest_structure_and_counts(self, validator, manifest_data):
        """Manifest contains 4 chapters, >= 25 concepts, and 22 DAG edges."""
        report = validator.validate_manifest(manifest_data)
        assert report.is_valid is True
        assert report.failed_checks == 0
        assert len(manifest_data["chapters"]) == 4
        assert len(manifest_data["dagEdges"]) == 22

    def test_dag_acyclicity_kahns_algorithm(self, validator, manifest_data):
        """Kahn's topological sort O(V + E) verifies acyclicity and visits all 25 concepts."""
        declared_concepts = []
        for ch in manifest_data["chapters"]:
            for c in ch["concepts"]:
                declared_concepts.append(c["id"])

        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(
            declared_concepts, manifest_data["dagEdges"]
        )
        assert is_acyclic is True
        assert error_msg == ""
        assert len(topo_order) == 25
        # Inter-chapter dependency: Polynomials zeroes must precede Quadratic standard form
        poly_coeff_idx = topo_order.index("cbse-10-math-poly-coefficients-zeros")
        quad_std_idx = topo_order.index("cbse-10-math-quad-standard-form")
        assert poly_coeff_idx < quad_std_idx, "Polynomials must precede Quadratics in topological order"

    def test_dag_cycle_detection_and_path_reporting(self, validator):
        """Kahn's algorithm detects intentional cycles and extracts the cycle path."""
        concepts = ["c1", "c2", "c3"]
        # Introducing cycle: c1 -> c2 -> c3 -> c1
        cycle_edges = [
            {"fromConceptId": "c1", "toConceptId": "c2"},
            {"fromConceptId": "c2", "toConceptId": "c3"},
            {"fromConceptId": "c3", "toConceptId": "c1"},
        ]
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(
            concepts, cycle_edges
        )
        assert is_acyclic is False
        assert len(topo_order) == 0
        assert "Cycle detected" in error_msg
        assert "c1" in error_msg and "c2" in error_msg and "c3" in error_msg

    def test_concept_referential_integrity(self, validator, manifest_data):
        """Validator rejects edges referencing undeclared concepts."""
        tampered_manifest = copy.deepcopy(manifest_data)
        tampered_manifest["dagEdges"].append({
            "fromConceptId": "cbse-10-math-real-numbers-fta",
            "toConceptId": "non-existent-concept-xyz",
            "relationship": "prerequisite",
            "weight": 1.0,
        })
        report = validator.validate_manifest(tampered_manifest)
        assert report.is_valid is False
        assert any("dag_edge_referential_integrity" in c.name and not c.passed for c in report.checks)

    def test_self_loops_rejected(self, validator, manifest_data):
        """Validator rejects self-loops (A -> A)."""
        tampered = copy.deepcopy(manifest_data)
        tampered["dagEdges"].append({
            "fromConceptId": "cbse-10-math-real-numbers-fta",
            "toConceptId": "cbse-10-math-real-numbers-fta",
            "relationship": "prerequisite",
            "weight": 1.0,
        })
        report = validator.validate_manifest(tampered)
        assert report.is_valid is False
        assert any("dag_no_self_loops" in c.name and not c.passed for c in report.checks)

    def test_source_rights_rule6_rule10(self, validator):
        """Empty sourceRefs requires translationStatus or rights to be 'original'."""
        valid_pkg = {
            "schemaVersion": "1.0.0",
            "lessonId": "test-valid",
            "title": "Valid Package",
            "grade": 10,
            "subjectId": "subject-math",
            "translationStatus": "original",
            "blocks": [{"blockId": "b1", "kind": "summary", "content": "Sample"}],
            "takeaways": ["Takeaway 1"],
            "validation": {"status": "ready", "checks": []},
            "sourceRefs": [],
        }
        report_valid = validator.validate_resource_package(valid_pkg)
        assert any("source_rights" in c.name and c.passed for c in report_valid.checks)

        invalid_pkg = copy.deepcopy(valid_pkg)
        invalid_pkg["translationStatus"] = "ai_draft_unreviewed"
        report_invalid = validator.validate_resource_package(invalid_pkg)
        assert any("source_rights" in c.name and not c.passed for c in report_invalid.checks)

    def test_all_20_resource_packages_and_4_diagnostics_conformance(self, validator):
        """Entire CBSE 10 Math content library validates cleanly with 0 failures."""
        master_report = validator.validate_content_library(CONTENT_DIR)
        assert master_report.is_valid is True
        assert master_report.failed_checks == 0
        assert master_report.passed_checks >= 80


# ==============================================================================
# 2. PACKAGE REDACTION SERVICE TESTS
# ==============================================================================

class TestPackageRedaction:
    @pytest.fixture
    def sample_package(self):
        return {
            "lessonId": "real-numbers-practice-set",
            "title": "Practice Set",
            "blocks": [{"blockId": "b1", "kind": "summary", "content": "Overview"}],
            "workedExamples": [
                {
                    "prompt": "Find HCF of 12 and 18",
                    "steps": ["Step 1: 12 = 2^2 * 3", "Step 2: 18 = 2 * 3^2", "Step 3: HCF = 6"],
                    "answer": "6",
                }
            ],
            "practice": [
                {
                    "questionId": "q1",
                    "type": "multiple_choice",
                    "prompt": "What is the HCF of 12 and 18?",
                    "options": ["2", "3", "6", "9"],
                    "answerKey": 2,
                    "explanation": "6 divides both 12 and 18 without remainder.",
                    "steps": ["Factorise 12 and 18", "Find common divisors"],
                    "feedback": "HCF is 6.",
                    "rubric": {
                        "math_verification": {"expected": 6},
                        "solution": "6 is the highest factor",
                    },
                }
            ],
            "checkpointTest": [
                {
                    "questionId": "q2",
                    "type": "multiple_choice",
                    "prompt": "What is LCM of 12 and 18?",
                    "options": ["18", "36", "72", "6"],
                    "answerKey": 1,
                    "correct_answer": "36",
                    "explanation": "LCM(12, 18) = 36.",
                    "feedback": "36 is the lowest common multiple.",
                }
            ],
        }

    def test_redact_question_package_student_role(self, sample_package):
        """Strips answerKey, explanation, steps, feedback from quiz items."""
        redacted = redact_question_package_for_student(sample_package)

        # Practice question checks
        p_q = redacted["practice"][0]
        assert "answerKey" not in p_q
        assert "explanation" not in p_q
        assert "steps" not in p_q
        assert "feedback" not in p_q
        assert "math_verification" not in p_q
        assert p_q.get("rubric", {}).get("solution") is None
        # Question text and options are preserved
        assert p_q["prompt"] == "What is the HCF of 12 and 18?"
        assert p_q["options"] == ["2", "3", "6", "9"]

        # Checkpoint question checks
        cp_q = redacted["checkpointTest"][0]
        assert "answerKey" not in cp_q
        assert "correct_answer" not in cp_q
        assert "explanation" not in cp_q

    def test_redact_preserves_worked_examples_and_blocks(self, sample_package):
        """Worked examples are educational and strictly retain their steps and answers."""
        redacted = redact_question_package_for_student(sample_package)
        we = redacted["workedExamples"][0]
        assert we["prompt"] == "Find HCF of 12 and 18"
        assert len(we["steps"]) == 3
        assert we["answer"] == "6"
        assert redacted["blocks"][0]["content"] == "Overview"

    def test_redact_does_not_mutate_original_dict(self, sample_package):
        """Redaction function is pure and returns a new object without in-place mutation."""
        original_copy = copy.deepcopy(sample_package)
        _ = redact_question_package_for_student(sample_package)
        assert sample_package == original_copy
        assert "answerKey" in sample_package["practice"][0]

    def test_redact_diagnostic_bank(self):
        """Redaction cleanly strips answers and internal evaluations from diagnostic banks."""
        diag_bank = {
            "chapterId": "real-numbers",
            "items": [
                {
                    "questionId": "d1",
                    "prompt": "HCF of 6 and 20?",
                    "options": ["2", "4", "6", "10"],
                    "answerKey": 0,
                    "explanation": "HCF is 2.",
                    "math_verification": {"hcf": 2},
                }
            ],
        }
        redacted = redact_diagnostic_bank(diag_bank)
        item = redacted["items"][0]
        assert "answerKey" not in item
        assert "explanation" not in item
        assert "math_verification" not in item
        assert item["options"] == ["2", "4", "6", "10"]


# ==============================================================================
# 3. SYMPY MATHEMATICAL SOLVER TESTS
# ==============================================================================

class TestSympyMathVerification:
    @pytest.fixture
    def verifier(self):
        return LibraryMathVerifier(CONTENT_DIR)

    def test_real_numbers_hcf_lcm_identity(self, verifier):
        """Sympy verifies HCF * LCM = a * b identity."""
        passed, details, target = verifier.verify_real_numbers("test-1", {
            "subdomain": "hcf_lcm",
            "inputs": {"a": 96, "b": 404},
            "expected": {"hcf": 4, "lcm": 9696, "target_val": "9696"},
        })
        assert passed is True
        assert "HCF=4" in details and "LCM=9696" in details

    def test_real_numbers_prime_factorisation(self, verifier):
        """Sympy verifies prime factorisation decomposition."""
        passed, details, target = verifier.verify_real_numbers("test-2", {
            "subdomain": "prime_factorization",
            "inputs": {"n": 3825},
            "expected": {"target_val": "3^2 * 5^2 * 17"},
        })
        assert passed is True
        assert "3: 2, 5: 2, 17: 1" in details

    def test_real_numbers_terminating_decimals(self, verifier):
        """Sympy verifies denominator prime factors form 2^n * 5^m."""
        # 17 / 8 = 17 / 2^3 -> Terminating
        passed_term, _, _ = verifier.verify_real_numbers("test-3", {
            "subdomain": "terminating_decimal",
            "inputs": {"p": 17, "q": 8},
            "expected": {"terminating": True},
        })
        assert passed_term is True

        # 64 / 455 -> 455 = 5 * 7 * 13 -> Non-terminating repeating
        passed_non_term, _, _ = verifier.verify_real_numbers("test-4", {
            "subdomain": "terminating_decimal",
            "inputs": {"p": 64, "q": 455},
            "expected": {"terminating": False},
        })
        assert passed_non_term is True

    def test_polynomials_zeroes_and_vieta_relations(self, verifier):
        """Sympy verifies zeroes and coefficient relations: alpha + beta = -b/a, alpha * beta = c/a."""
        passed, details, _ = verifier.verify_polynomials("test-5", {
            "subdomain": "coeff_relations",
            "inputs": {"poly": "2*x**2 - 8*x + 6"},
            "expected": {"target_val": "4"},
        })
        assert passed is True
        assert "Sum=4" in details and "Product=3" in details

    def test_linear_systems_classification_and_solutions(self, verifier):
        """Sympy verifies unique solution and determinant consistency."""
        passed, details, target = verifier.verify_linear_equations("test-6", {
            "subdomain": "unique_solution",
            "inputs": {"eq1": "x + y - 14", "eq2": "x - y - 4"},
            "expected": {"solution": ["9", "5"], "target_val": "x = 9, y = 5"},
        })
        assert passed is True
        assert "(9, 5)" in details

    def test_quadratic_discriminant_and_nature_of_roots(self, verifier):
        """Sympy verifies discriminant D = b^2 - 4ac and roots."""
        # Positive D -> distinct real roots
        p1, _, _ = verifier.verify_quadratic_equations("test-7", {
            "subdomain": "nature_of_roots",
            "inputs": {"a": 1, "b": -5, "c": 6},
            "expected": {"discriminant": 1, "nature": "two_distinct_real_roots"},
        })
        assert p1 is True

        # Zero D -> equal real roots
        p2, _, _ = verifier.verify_quadratic_equations("test-8", {
            "subdomain": "nature_of_roots",
            "inputs": {"a": 1, "b": -4, "c": 4},
            "expected": {"discriminant": 0, "nature": "two_equal_real_roots"},
        })
        assert p2 is True

        # Negative D -> no real roots
        p3, _, _ = verifier.verify_quadratic_equations("test-9", {
            "subdomain": "nature_of_roots",
            "inputs": {"a": 2, "b": -4, "c": 3},
            "expected": {"discriminant": -8, "nature": "no_real_roots"},
        })
        assert p3 is True

    def test_verify_all_128_library_math_items_pass(self, verifier):
        """Comprehensive verification of 100% of quiz items across all 20 packages and 4 diagnostics."""
        exit_code = verifier.run()
        assert exit_code == 0
        assert verifier.total_verified == 128
        assert verifier.passed_count == 128
        assert verifier.failed_count == 0


# ==============================================================================
# 4. LIBRARY SEEDER TESTS
# ==============================================================================

class TestLibrarySeeder:
    @pytest.fixture
    def seeder(self):
        return LibrarySeeder(manifest_path=MANIFEST_PATH)

    def test_system_owner_attribution(self):
        """System owner is strictly UUID 00000000-0000-0000-0000-000000000001."""
        assert str(SYSTEM_OWNER_ID) == "00000000-0000-0000-0000-000000000001"

    def test_validate_only_mode(self, seeder):
        """Validate-only mode returns passed validation report without DB writes."""
        report = seeder.validate_only()
        assert report.is_valid is True
        assert report.failed_checks == 0
        assert report.passed_checks >= 80

    def test_manifest_sha256_hash_reproducibility(self, seeder):
        """Manifest hash is reproducible and 64 hex characters."""
        hash1 = seeder.compute_manifest_hash()
        hash2 = seeder.compute_manifest_hash()
        assert hash1 == hash2
        assert len(hash1) == 64
