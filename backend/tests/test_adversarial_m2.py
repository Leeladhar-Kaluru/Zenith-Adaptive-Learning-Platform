"""Adversarial Stress Test Suite for Milestone 2:
Curriculum Content Engine & Math Packages.

Targeting:
1. DAG Cycle Detection and Topological Sorting (`library_validator.py`)
2. Package Redaction Service (`package_redaction.py`)
3. Seeder Validate-Only Idempotency (`library_seed.py`)
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import pytest

from app.services.library_validator import LibraryValidator, ValidationReport
from app.services.package_redaction import (
    redact_question_package_for_student,
    redact_single_question_for_student,
    redact_resource_package,
    redact_diagnostic_bank,
    QUESTION_STRIP_KEYS,
)
from app.services.library_seed import LibrarySeeder, SYSTEM_OWNER_ID

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content", "library", "cbse-10-math")
MANIFEST_PATH = os.path.join(CONTENT_DIR, "manifest.json")


# ==============================================================================
# SECTION 1: ADVERSARIAL DAG STRESS TESTS
# ==============================================================================

class TestAdversarialDAG:
    """Stress tests for validate_dag_kahns_algorithm and cycle path extraction."""

    @pytest.fixture
    def validator(self):
        return LibraryValidator()

    def test_dag_two_node_cycle(self, validator):
        """Edge case: 2-node cycle A -> B -> A must be rejected with accurate cycle path."""
        concepts = ["A", "B"]
        edges = [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "A"},
        ]
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(concepts, edges)
        assert is_acyclic is False
        assert topo_order == []
        assert "Cycle detected" in error_msg
        assert ("A -> B -> A" in error_msg) or ("B -> A -> B" in error_msg)

    def test_dag_three_node_cycle(self, validator):
        """Edge case: 3-node cycle A -> B -> C -> A must be rejected with accurate cycle path."""
        concepts = ["A", "B", "C"]
        edges = [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "A"},
        ]
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(concepts, edges)
        assert is_acyclic is False
        assert topo_order == []
        assert "Cycle detected" in error_msg
        assert any(
            pattern in error_msg
            for pattern in [
                "A -> B -> C -> A",
                "B -> C -> A -> B",
                "C -> A -> B -> C",
            ]
        )

    def test_dag_self_loop(self, validator):
        """Edge case: Self-loop A -> A must be rejected with accurate cycle path."""
        concepts = ["A"]
        edges = [
            {"from": "A", "to": "A"},
        ]
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(concepts, edges)
        assert is_acyclic is False
        assert topo_order == []
        assert "Cycle detected" in error_msg
        assert "A -> A" in error_msg

    def test_dag_disconnected_components_one_cyclic(self, validator):
        """Edge case: Disconnected components where C1 is acyclic and C2 is cyclic."""
        # C1: X -> Y -> Z (acyclic)
        # C2: A -> B -> C -> A (cyclic)
        concepts = ["X", "Y", "Z", "A", "B", "C"]
        edges = [
            {"from": "X", "to": "Y"},
            {"from": "Y", "to": "Z"},
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "A"},
        ]
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(concepts, edges)
        assert is_acyclic is False
        assert topo_order == []
        assert "Cycle detected" in error_msg
        # Cycle path must isolate C2 cycle and NOT include X, Y, or Z
        assert "X" not in error_msg
        assert "Y" not in error_msg
        assert "Z" not in error_msg
        assert any(
            p in error_msg
            for p in ["A -> B -> C -> A", "B -> C -> A -> B", "C -> A -> B -> C"]
        )

    def test_dag_diamond_dag_succeeds_with_valid_topological_order(self, validator):
        """Edge case: Diamond DAG A -> B, A -> C, B -> D, C -> D must succeed."""
        concepts = ["A", "B", "C", "D"]
        edges = [
            {"fromConceptId": "A", "toConceptId": "B"},
            {"fromConceptId": "A", "toConceptId": "C"},
            {"fromConceptId": "B", "toConceptId": "D"},
            {"fromConceptId": "C", "toConceptId": "D"},
        ]
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(concepts, edges)
        assert is_acyclic is True
        assert error_msg == ""
        assert len(topo_order) == 4
        # Validate topological invariants
        idx_a = topo_order.index("A")
        idx_b = topo_order.index("B")
        idx_c = topo_order.index("C")
        idx_d = topo_order.index("D")
        assert idx_a < idx_b < idx_d
        assert idx_a < idx_c < idx_d

    def test_dag_empty_graph(self, validator):
        """Edge case: Empty graph with 0 nodes and 0 edges must succeed."""
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm([], [])
        assert is_acyclic is True
        assert topo_order == []
        assert error_msg == ""

    def test_dag_single_node_graph(self, validator):
        """Edge case: Single isolated node with 0 edges must succeed."""
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(["Solo"], [])
        assert is_acyclic is True
        assert topo_order == ["Solo"]
        assert error_msg == ""

    def test_dag_long_chain_stress(self, validator):
        """Stress test: 50-node linear chain A0 -> A1 -> ... -> A49 must return exact linear order."""
        n = 50
        concepts = [f"node_{i}" for i in range(n)]
        edges = [{"from": f"node_{i}", "to": f"node_{i+1}"} for i in range(n - 1)]
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(concepts, edges)
        assert is_acyclic is True
        assert error_msg == ""
        assert topo_order == concepts

    def test_dag_undeclared_concept_reference(self, validator):
        """Adversarial edge referencing undeclared node must fail cleanly."""
        concepts = ["A", "B"]
        edges = [{"from": "A", "to": "GHOST"}]
        is_acyclic, topo_order, error_msg = validator.validate_dag_kahns_algorithm(concepts, edges)
        assert is_acyclic is False
        assert "references undeclared concept" in error_msg

    def test_dag_manifest_validation_rejects_cycle_in_full_pipeline(self, validator):
        """Manifest validator detects cycle injected into full CBSE manifest."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        tampered = copy.deepcopy(manifest_data)
        # Add back-edge creating cycle between Real Numbers concepts
        tampered["dagEdges"].append({
            "fromConceptId": "cbse-10-math-real-numbers-fta-applications",
            "toConceptId": "cbse-10-math-real-numbers-fta",
            "relationship": "prerequisite",
            "weight": 1.0,
        })
        report = validator.validate_manifest(tampered)
        assert report.is_valid is False
        assert any("dag_acyclicity" in c.name and not c.passed for c in report.checks)


# ==============================================================================
# SECTION 2: ADVERSARIAL PACKAGE REDACTION STRESS TESTS
# ==============================================================================

class TestAdversarialPackageRedaction:
    """Stress tests for package redaction across question types, deep nesting, worked examples, and immutability."""

    def test_redact_multiple_question_formats(self):
        """Tests redaction across multiple-choice, numerical, and multi-select question types."""
        package = {
            "lessonId": "multi-format-test",
            "practice": [
                {
                    "questionId": "q_mc",
                    "type": "multiple_choice",
                    "prompt": "Choose the prime number:",
                    "options": ["4", "6", "7", "9"],
                    "answerKey": 2,
                    "explanation": "7 has only 1 and itself as factors.",
                    "steps": ["Test divisibility"],
                    "feedback": "Correct, 7 is prime.",
                },
                {
                    "questionId": "q_num",
                    "type": "numerical",
                    "prompt": "Calculate 15 * 14:",
                    "answer_key": 210,
                    "correct_answer": 210,
                    "tolerance": 0.0,
                    "explanation": "15 * 14 = 210",
                    "solution": "Multiplication steps: 15 * 10 + 15 * 4 = 150 + 60 = 210",
                },
                {
                    "questionId": "q_ms",
                    "type": "multi_select",
                    "prompt": "Select all irrational numbers:",
                    "options": ["sqrt(2)", "1/3", "pi", "0.25"],
                    "answerKey": [0, 2],
                    "correctAnswer": ["sqrt(2)", "pi"],
                    "feedback": "sqrt(2) and pi are irrational.",
                    "math_verification": {"expected_indices": [0, 2]},
                },
            ],
            "checkpointTest": [
                {
                    "questionId": "q_chk_1",
                    "type": "multiple_choice",
                    "prompt": "Evaluate HCF(10, 15):",
                    "options": ["1", "5", "10", "15"],
                    "answerKey": 1,
                    "correct_answer": "5",
                    "explanation": "5 is highest common factor",
                }
            ],
        }

        redacted = redact_question_package_for_student(package)

        for container in ["practice", "checkpointTest"]:
            for q in redacted[container]:
                for sensitive_key in [
                    "answerKey",
                    "answer_key",
                    "correct_answer",
                    "correctAnswer",
                    "explanation",
                    "solution",
                    "steps",
                    "feedback",
                    "math_verification",
                ]:
                    assert sensitive_key not in q, f"Key '{sensitive_key}' leaked in {q.get('questionId')}"

        # Verify legitimate fields remain intact
        assert redacted["practice"][0]["options"] == ["4", "6", "7", "9"]
        assert redacted["practice"][1]["tolerance"] == 0.0
        assert redacted["practice"][2]["options"] == ["sqrt(2)", "1/3", "pi", "0.25"]

    def test_redact_rubric_sanitization(self):
        """Tests that devtools leakage via question rubric fields is thoroughly purged."""
        question = {
            "questionId": "rubric_leak_test",
            "type": "free_response",
            "prompt": "State the Fundamental Theorem of Arithmetic.",
            "rubric": {
                "max_score": 3,
                "criteria": ["Uniqueness", "Prime factorization", "Order irrelevance"],
                "answer": "Every composite number can be expressed as a unique product of primes...",
                "solution": "Full theorem statement",
                "expected": "Unique factorisation",
                "criteria_answers": {"c1": "primes", "c2": "unique"},
                "math_verification": {"verified": True},
            },
        }

        redacted = redact_single_question_for_student(question)
        rubric = redacted.get("rubric", {})
        assert rubric.get("max_score") == 3
        assert rubric.get("criteria") == ["Uniqueness", "Prime factorization", "Order irrelevance"]
        assert "answer" not in rubric
        assert "solution" not in rubric
        assert "expected" not in rubric
        assert "criteria_answers" not in rubric
        assert "math_verification" not in rubric

    def test_worked_examples_and_blocks_strictly_preserved(self):
        """Assert that workedExamples (prompt, steps, answer), blocks, and visual specs are NEVER stripped."""
        package = {
            "lessonId": "worked-examples-preservation-test",
            "title": "Worked Examples Integrity",
            "blocks": [
                {"blockId": "b1", "kind": "heading", "content": "Introduction"},
                {"blockId": "b2", "kind": "paragraph", "content": "Polynomial zeroes concept"},
            ],
            "visuals": [
                {
                    "visualId": "vis-1",
                    "spec": {"type": "parabola", "axis": "vertical", "vertex": [0, -4]},
                }
            ],
            "workedExamples": [
                {
                    "exampleId": "we-1",
                    "prompt": "Find the zeroes of the quadratic polynomial x^2 + 7x + 10.",
                    "steps": [
                        "Step 1: Factorise the polynomial: x^2 + 5x + 2x + 10 = (x + 5)(x + 2)",
                        "Step 2: Set equal to zero: (x + 5)(x + 2) = 0",
                        "Step 3: Solve for x: x = -5 or x = -2",
                    ],
                    "answer": "The zeroes are -2 and -5.",
                },
                {
                    "exampleId": "we-2",
                    "prompt": "Verify the relationship between zeroes and coefficients.",
                    "steps": [
                        "Sum of zeroes = -2 + (-5) = -7 = -(7)/1 = -b/a",
                        "Product of zeroes = (-2) * (-5) = 10 = 10/1 = c/a",
                    ],
                    "answer": "Relationships verified.",
                },
            ],
            "practice": [
                {
                    "questionId": "p-1",
                    "prompt": "Find zeroes of x^2 - 3.",
                    "answerKey": 0,
                    "explanation": "x = +/- sqrt(3)",
                }
            ],
        }

        redacted = redact_question_package_for_student(package)

        # 1. Blocks preserved
        assert len(redacted["blocks"]) == 2
        assert redacted["blocks"][0]["content"] == "Introduction"
        assert redacted["blocks"][1]["content"] == "Polynomial zeroes concept"

        # 2. Visuals preserved
        assert len(redacted["visuals"]) == 1
        assert redacted["visuals"][0]["visualId"] == "vis-1"
        assert redacted["visuals"][0]["spec"]["vertex"] == [0, -4]

        # 3. Worked examples preserved with full educational steps and answers
        assert len(redacted["workedExamples"]) == 2
        we1 = redacted["workedExamples"][0]
        assert we1["prompt"] == "Find the zeroes of the quadratic polynomial x^2 + 7x + 10."
        assert len(we1["steps"]) == 3
        assert we1["answer"] == "The zeroes are -2 and -5."

        we2 = redacted["workedExamples"][1]
        assert len(we2["steps"]) == 2
        assert we2["answer"] == "Relationships verified."

        # 4. Practice quiz question is properly redacted
        p1 = redacted["practice"][0]
        assert "answerKey" not in p1
        assert "explanation" not in p1
        assert p1["prompt"] == "Find zeroes of x^2 - 3."

    def test_input_dict_not_mutated_in_place(self):
        """Assert that the input dictionary passed to redaction is NOT mutated in-place."""
        original = {
            "lessonId": "immutability-test",
            "practice": [
                {
                    "questionId": "q1",
                    "prompt": "Test?",
                    "options": ["A", "B"],
                    "answerKey": 0,
                    "explanation": "Secret explanation",
                    "feedback": "Secret feedback",
                }
            ],
            "checkpointTest": [
                {
                    "questionId": "q2",
                    "prompt": "Test 2?",
                    "correct_answer": "B",
                    "solution": "Secret solution",
                }
            ],
        }

        # Snapshot a deep copy before calling redaction
        before_call = copy.deepcopy(original)

        result = redact_question_package_for_student(original)

        # Original input MUST be completely unchanged
        assert original == before_call
        assert original["practice"][0]["answerKey"] == 0
        assert original["practice"][0]["explanation"] == "Secret explanation"
        assert original["checkpointTest"][0]["correct_answer"] == "B"

        # Redacted result MUST NOT have the sensitive keys
        assert "answerKey" not in result["practice"][0]
        assert "explanation" not in result["practice"][0]
        assert "correct_answer" not in result["checkpointTest"][0]

    def test_diagnostic_item_wrapped_in_question_json(self):
        """Tests redaction of diagnostic items that wrap their payload in question_json."""
        diag_data = {
            "diagnostic_items": [
                {
                    "id": "diag_row_1",
                    "concept_id": "c1",
                    "student_response": 2,
                    "is_correct": False,
                    "question_json": {
                        "questionId": "d_probe_1",
                        "prompt": "Probe question",
                        "options": ["Opt 1", "Opt 2"],
                        "answerKey": 1,
                        "explanation": "Internal probe rationale",
                        "math_verification": {"root": 4},
                        "rubric": {
                            "answer": "Opt 2",
                            "solution": "Full derivation",
                            "math_verification": {"root": 4},
                        },
                    },
                }
            ]
        }

        redacted = redact_question_package_for_student(diag_data)
        item = redacted["diagnostic_items"][0]

        # Student response and is_correct flags stripped
        assert "student_response" not in item
        assert "is_correct" not in item

        # Inner question_json redacted
        q_json = item["question_json"]
        assert "answerKey" not in q_json
        assert "explanation" not in q_json
        assert "math_verification" not in q_json
        assert q_json["prompt"] == "Probe question"
        assert q_json["options"] == ["Opt 1", "Opt 2"]

        # Inner rubric thoroughly sanitized
        inner_rubric = q_json.get("rubric", {})
        assert "answer" not in inner_rubric
        assert "solution" not in inner_rubric
        assert "math_verification" not in inner_rubric

    def test_all_24_content_packages_zero_redaction_leakage(self):
        """Validates that running redaction over all 20 packages and 4 diagnostic banks leaves 0 leaks."""
        import glob
        all_json = glob.glob(os.path.join(CONTENT_DIR, "*.json"))
        packages = [f for f in all_json if os.path.basename(f) not in ("manifest.json", "chapter.json")]
        assert len(packages) == 24

        for pkg_path in packages:
            fname = os.path.basename(pkg_path)
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            redacted = redact_question_package_for_student(data)

            # Check practice, checkpointTest, items
            for container in ["practice", "checkpointTest", "items"]:
                for q in redacted.get(container, []):
                    if isinstance(q, dict):
                        for sensitive_key in QUESTION_STRIP_KEYS:
                            assert sensitive_key not in q, f"Leak of {sensitive_key} in {fname}:{q.get('questionId')}"
                        if "rubric" in q and isinstance(q["rubric"], dict):
                            for rub_leak in ("answer", "solution", "expected", "criteria_answers", "math_verification"):
                                assert rub_leak not in q["rubric"], f"Leak of rubric.{rub_leak} in {fname}:{q.get('questionId')}"

    def test_empty_and_malformed_inputs(self):
        """Tests handling of non-dict, empty dict, and missing container inputs."""
        assert redact_single_question_for_student(None) is None
        assert redact_single_question_for_student("not-a-dict") == "not-a-dict"
        assert redact_single_question_for_student({}) == {}

        assert redact_question_package_for_student(None) is None
        assert redact_question_package_for_student([]) == []
        assert redact_question_package_for_student({}) == {}


# ==============================================================================
# SECTION 3: SEEDER VALIDATE-ONLY IDEMPOTENCY TESTS
# ==============================================================================

class TestAdversarialSeeder:
    """Stress tests for library seeder validate-only execution."""

    def test_validate_only_exits_zero_without_db_writes(self):
        """Runs seeder with --validate-only via subprocess to verify 0 exit code and zero DB writes."""
        cmd = [
            sys.executable,
            "-m",
            "app.services.library_seed",
            "--validate-only",
        ]
        result = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Seeder --validate-only failed: {result.stderr}\n{result.stdout}"
        assert "VALIDATE ONLY (Zero Database Writes)" in result.stdout
        assert "VALIDATION PASSED (EXIT CODE 0)" in result.stdout

    def test_seeder_fails_on_corrupt_manifest(self, tmp_path):
        """Seeder with --validate-only on cyclic manifest exits with code 1."""
        corrupt_manifest = tmp_path / "manifest.json"
        corrupt_data = {
            "board": {"id": "board-cbse", "code": "CBSE"},
            "grade": 10,
            "subject": {"id": "subject-math", "code": "MATH"},
            "chapters": [
                {
                    "id": "ch1",
                    "slug": "ch1",
                    "title": "Ch1",
                    "concepts": [{"id": "c1"}, {"id": "c2"}],
                    "resources": [],
                }
            ],
            "dagEdges": [
                {"fromConceptId": "c1", "toConceptId": "c2"},
                {"fromConceptId": "c2", "toConceptId": "c1"},  # Cycle!
            ],
        }
        corrupt_manifest.write_text(json.dumps(corrupt_data), encoding="utf-8")

        seeder = LibrarySeeder(manifest_path=str(corrupt_manifest))
        report = seeder.validate_only()
        assert report.is_valid is False
        assert any("dag_acyclicity" in c.name and not c.passed for c in report.checks)
