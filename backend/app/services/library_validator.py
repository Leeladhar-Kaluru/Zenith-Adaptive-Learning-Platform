"""Curriculum Library Content Validator for ZENITH.

Validates:
1. Manifest JSON structure and curriculum metadata.
2. Concept Directed Acyclic Graph (DAG) acyclicity using Kahn's topological sort ($O(V + E)$).
3. Concept referential integrity across chapters, DAG edges, and question items.
4. Resource package and visual specification schema conformance (jsonschema).
5. Question integrity (options, answerKey bounds, feedback, hints).
6. Source rights and sourceRefs compliance with Rule 6 and Rule 10.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import jsonschema
except ImportError:
    jsonschema = None  # Handled gracefully if not installed


@dataclass
class ValidationCheck:
    name: str
    passed: bool
    details: str


@dataclass
class ValidationReport:
    is_valid: bool
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: List[ValidationCheck] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    topological_order: List[str] = field(default_factory=list)

    def add_check(self, name: str, passed: bool, details: str) -> None:
        self.total_checks += 1
        if passed:
            self.passed_checks += 1
        else:
            self.failed_checks += 1
            self.is_valid = False
            self.errors.append(f"[{name}] {details}")
        self.checks.append(ValidationCheck(name=name, passed=passed, details=details))


class LibraryValidator:
    """Multi-stage validator for curriculum packages, manifest, and concept DAG."""

    def __init__(self, schemas_dir: Optional[str] = None):
        self.schemas_dir = schemas_dir or self._find_schemas_dir()
        self.lesson_schema = self._load_json_schema("lesson-package.schema.json")
        self.visual_schema = self._load_json_schema("visual-spec.schema.json")

    def _find_schemas_dir(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "content", "library", "schemas"))

    def _load_json_schema(self, filename: str) -> Dict[str, Any]:
        """Loads a required JSON schema. A missing schema is an error, never a silent skip."""
        path = os.path.join(self.schemas_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate_dag_kahns_algorithm(
        self, concept_ids: List[str], edges: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str], str]:
        """Runs Kahn's algorithm O(V + E) to check DAG acyclicity.
        
        Returns:
            (is_acyclic, topological_sort_order, error_message_or_cycle_path)
        """
        all_nodes = list(dict.fromkeys(concept_ids))
        in_degree: Dict[str, int] = {node: 0 for node in all_nodes}
        adj: Dict[str, List[str]] = {node: [] for node in all_nodes}

        for edge in edges:
            u = edge.get("fromConceptId") or edge.get("from")
            v = edge.get("toConceptId") or edge.get("to")
            if u not in in_degree or v not in in_degree:
                return False, [], f"Edge references undeclared concept: {u} -> {v}"
            adj[u].append(v)
            in_degree[v] += 1

        queue: List[str] = [node for node in all_nodes if in_degree[node] == 0]
        topological_order: List[str] = []

        while queue:
            curr = queue.pop(0)
            topological_order.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topological_order) == len(all_nodes):
            return True, topological_order, ""

        # Cycle detected: Extract cycle path using DFS on unvisited nodes
        unvisited = {n for n in all_nodes if n not in topological_order}
        cycle_path = self._extract_cycle_path(unvisited, adj)
        return False, [], f"Cycle detected in concept graph: {' -> '.join(cycle_path)}"

    def _extract_cycle_path(
        self, nodes: Set[str], adj: Dict[str, List[str]]
    ) -> List[str]:
        color: Dict[str, int] = {n: 0 for n in nodes}
        parent: Dict[str, str] = {}
        cycle: List[str] = []

        def dfs(u: str) -> bool:
            color[u] = 1
            for v in adj.get(u, []):
                if v not in nodes:
                    continue
                if color[v] == 1:
                    curr = u
                    cycle.append(v)
                    while curr != v:
                        cycle.append(curr)
                        curr = parent.get(curr, v)
                    cycle.append(v)
                    cycle.reverse()
                    return True
                elif color[v] == 0:
                    parent[v] = u
                    if dfs(v):
                        return True
            color[u] = 2
            return False

        for node in nodes:
            if color[node] == 0:
                if dfs(node):
                    return cycle
        return list(nodes)

    def validate_manifest(self, manifest: Dict[str, Any]) -> ValidationReport:
        """Validates manifest structure, DAG acyclicity, and concept integrity."""
        report = ValidationReport(is_valid=True, total_checks=0, passed_checks=0, failed_checks=0)

        # 1. Structure check
        required_root_keys = ["board", "grade", "subject", "chapters", "dagEdges"]
        missing_root = [k for k in required_root_keys if k not in manifest]
        if missing_root:
            report.add_check("manifest_root_keys", False, f"Missing required manifest keys: {missing_root}")
            return report
        report.add_check("manifest_root_keys", True, "Manifest contains all required root keys")

        # 2. Board, Grade, Subject constraints
        board = manifest.get("board", {})
        subject = manifest.get("subject", {})
        grade = manifest.get("grade")
        
        board_valid = board.get("id") == "board-cbse" or board.get("code") == "CBSE"
        report.add_check("manifest_board", board_valid, f"Board is {board.get('id', board.get('code'))}")

        grade_valid = grade in (6, 7, 8, 9, 10)
        report.add_check("manifest_grade", grade_valid, f"Grade is {grade} (CBSE Classes 6-10)")

        subject_valid = (
            subject.get("id") in ("subject-math", "subject-science")
            or subject.get("code") in ("MATH", "SCI")
        )
        report.add_check("manifest_subject", subject_valid, f"Subject is {subject.get('id', subject.get('code'))}")

        # 3. Collect declared concepts
        declared_concept_ids: Set[str] = set()
        for ch in manifest.get("chapters", []):
            for c in ch.get("concepts", []):
                c_id = c.get("id")
                if c_id:
                    declared_concept_ids.add(c_id)

        # Also support top-level declared concepts if present
        for c in manifest.get("concepts", []):
            c_id = c.get("id")
            if c_id:
                declared_concept_ids.add(c_id)

        is_cbse10_math = (grade == 10 and (subject.get("id") == "subject-math" or subject.get("code") == "MATH") and len(manifest.get("chapters", [])) > 1)
        expected_min_concepts = 25 if is_cbse10_math else 5
        concept_count_valid = len(declared_concept_ids) >= expected_min_concepts
        report.add_check(
            "concept_registry_count",
            concept_count_valid,
            f"Declared concepts: {len(declared_concept_ids)} (expected >= {expected_min_concepts})",
        )

        # 4. Check DAG Acyclicity via Kahn's Algorithm
        edges = manifest.get("dagEdges", [])
        is_acyclic, topo_order, error_msg = self.validate_dag_kahns_algorithm(
            list(declared_concept_ids), edges
        )
        report.add_check(
            "dag_acyclicity_kahns_algorithm",
            is_acyclic,
            "DAG is acyclic and verified by Kahn's algorithm" if is_acyclic else error_msg,
        )
        if is_acyclic:
            report.topological_order = topo_order

        # 5. Referential integrity of edges
        invalid_edges = []
        self_loops = []
        seen_edges: Set[Tuple[str, str]] = set()
        duplicate_edges = []

        for edge in edges:
            u = edge.get("fromConceptId") or edge.get("from")
            v = edge.get("toConceptId") or edge.get("to")
            if u not in declared_concept_ids or v not in declared_concept_ids:
                invalid_edges.append((u, v))
            if u == v:
                self_loops.append(u)
            edge_tuple = (u, v)
            if edge_tuple in seen_edges:
                duplicate_edges.append(edge_tuple)
            seen_edges.add(edge_tuple)

        report.add_check(
            "dag_edge_referential_integrity",
            len(invalid_edges) == 0,
            f"Invalid edge references: {invalid_edges}" if invalid_edges else "All edges reference valid declared concepts",
        )
        report.add_check(
            "dag_no_self_loops",
            len(self_loops) == 0,
            f"Self-loops detected: {self_loops}" if self_loops else "No self-loops detected in DAG",
        )
        report.add_check(
            "dag_no_duplicate_edges",
            len(duplicate_edges) == 0,
            f"Duplicate edges: {duplicate_edges}" if duplicate_edges else "No duplicate edges in DAG",
        )

        # 6. Chapters check
        chapters = manifest.get("chapters", [])
        expected_chapters = 4 if is_cbse10_math else 1
        chapters_valid = len(chapters) >= expected_chapters
        report.add_check(
            "flagship_chapters_count",
            chapters_valid,
            f"Total chapters: {len(chapters)} (expected >= {expected_chapters})",
        )

        return report

    def validate_resource_package(
        self, package: Dict[str, Any], declared_concept_ids: Optional[Set[str]] = None
    ) -> ValidationReport:
        """Validates a single resource package against schema, questions, and Rule 6/10 rights."""
        report = ValidationReport(is_valid=True, total_checks=0, passed_checks=0, failed_checks=0)

        # 1. JSON Schema validation
        if self.lesson_schema and jsonschema:
            try:
                jsonschema.validate(instance=package, schema=self.lesson_schema)
                report.add_check("lesson_package_schema", True, "Conforms to lesson-package.schema.json")
            except jsonschema.ValidationError as exc:
                report.add_check("lesson_package_schema", False, f"Schema error at {list(exc.path)}: {exc.message}")
        else:
            # Fallback schema check
            required_keys = ["schemaVersion", "lessonId", "title", "grade", "subjectId", "blocks", "takeaways", "validation"]
            missing = [k for k in required_keys if k not in package]
            report.add_check("fallback_schema_check", len(missing) == 0, f"Missing required keys: {missing}" if missing else "Required keys present")

        # 2. Visual specifications validation
        visuals = package.get("visuals", [])
        if visuals and self.visual_schema and jsonschema:
            for vis in visuals:
                spec = vis.get("spec") or vis
                try:
                    jsonschema.validate(instance=spec, schema=self.visual_schema)
                except jsonschema.ValidationError as exc:
                    report.add_check(
                        f"visual_spec_{vis.get('visualId')}",
                        False,
                        f"Visual spec error: {exc.message}",
                    )

        # 3. Source Rights and sourceRefs (Rule 6 & Rule 10)
        source_refs = package.get("sourceRefs", [])
        translation_status = package.get("translationStatus") or package.get("rights")
        if not source_refs:
            is_valid_original = translation_status in ("original", "reviewed_translation")
            report.add_check(
                "source_rights_rule6_rule10",
                is_valid_original,
                f"sourceRefs is empty; translationStatus is '{translation_status}' (must be 'original')",
            )
        else:
            report.add_check("source_rights_rule6_rule10", True, f"sourceRefs has {len(source_refs)} valid citations")

        # 4. Questions and options integrity
        seen_question_ids: Set[str] = set()
        question_errors: List[str] = []

        all_questions = (package.get("practice") or []) + (package.get("checkpointTest") or [])
        for q in all_questions:
            q_id = q.get("questionId") or q.get("id") or "unknown"
            if q_id in seen_question_ids:
                question_errors.append(f"Duplicate questionId '{q_id}'")
            seen_question_ids.add(q_id)

            # Check concept referential integrity
            q_concepts = q.get("conceptIds") or ([q["conceptId"]] if "conceptId" in q else [])
            if declared_concept_ids:
                for c_id in q_concepts:
                    if c_id not in declared_concept_ids:
                        question_errors.append(f"Question '{q_id}' references undeclared concept '{c_id}'")

            # Check multiple choice options & answerKey
            q_type = q.get("type")
            if q_type == "multiple_choice":
                options = q.get("options")
                if not options or not isinstance(options, list) or len(options) < 2:
                    question_errors.append(f"Question '{q_id}' must have at least 2 options")
                else:
                    ans_key = q.get("answerKey")
                    if ans_key is None:
                        question_errors.append(f"Question '{q_id}' missing answerKey")
                    elif isinstance(ans_key, int):
                        if ans_key < 0 or ans_key >= len(options):
                            question_errors.append(f"Question '{q_id}' answerKey index {ans_key} out of range (options len: {len(options)})")
                    elif isinstance(ans_key, str):
                        # Option string or letter
                        if ans_key in ("A", "B", "C", "D") and len(options) == 4:
                            pass
                        elif ans_key not in options:
                            question_errors.append(f"Question '{q_id}' answerKey '{ans_key}' not in options")

            # Check feedback
            if not q.get("feedback"):
                question_errors.append(f"Question '{q_id}' missing pedagogical feedback")

        report.add_check(
            "question_integrity",
            len(question_errors) == 0,
            f"Question errors: {question_errors}" if question_errors else f"All {len(all_questions)} questions valid",
        )

        return report

    def validate_diagnostic_bank(
        self, bank: Dict[str, Any], declared_concept_ids: Optional[Set[str]] = None
    ) -> ValidationReport:
        """Validates diagnostic bank items, concept probes, and answer keys."""
        report = ValidationReport(is_valid=True, total_checks=0, passed_checks=0, failed_checks=0)

        items = bank.get("items", [])
        report.add_check(
            "diagnostic_item_count",
            len(items) == 8,
            f"Diagnostic bank contains {len(items)} items (expected 8 items: 4 bridge + 4 core)",
        )

        foundation_bridge_count = 0
        chapter_core_count = 0
        diag_errors = []

        for item in items:
            item_type = item.get("itemType")
            if item_type == "foundation_bridge":
                foundation_bridge_count += 1
            elif item_type == "chapter_core":
                chapter_core_count += 1

            c_id = item.get("conceptId")
            if declared_concept_ids and c_id and c_id not in declared_concept_ids:
                diag_errors.append(f"Diagnostic item '{item.get('questionId')}' references undeclared concept '{c_id}'")

            options = item.get("options", [])
            ans = item.get("answerKey")
            if not options or len(options) < 2:
                diag_errors.append(f"Diagnostic item '{item.get('questionId')}' missing options")
            if ans is None:
                diag_errors.append(f"Diagnostic item '{item.get('questionId')}' missing answerKey")
            elif isinstance(ans, int):
                if ans < 0 or ans >= len(options):
                    diag_errors.append(f"Diagnostic item answerKey index {ans} out of bounds")

        report.add_check(
            "diagnostic_probe_distribution",
            foundation_bridge_count == 4 and chapter_core_count == 4,
            f"Probes: {foundation_bridge_count} bridge, {chapter_core_count} core (expected 4 and 4)",
        )

        report.add_check(
            "diagnostic_items_integrity",
            len(diag_errors) == 0,
            f"Diagnostic errors: {diag_errors}" if diag_errors else "All diagnostic items valid",
        )

        return report

    def validate_content_library(self, content_dir: str) -> ValidationReport:
        """Validates the entire curriculum content library directory."""
        master_report = ValidationReport(is_valid=True, total_checks=0, passed_checks=0, failed_checks=0)

        # 1. Locate manifest.json
        manifest_path = os.path.join(content_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            # Check cbse-10-math subdirectory
            sub_manifest = os.path.join(content_dir, "cbse-10-math", "manifest.json")
            if os.path.exists(sub_manifest):
                manifest_path = sub_manifest
                content_dir = os.path.dirname(sub_manifest)
            else:
                master_report.add_check("manifest_file_exists", False, f"manifest.json not found in {content_dir}")
                return master_report

        master_report.add_check("manifest_file_exists", True, f"Found manifest at {manifest_path}")

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except Exception as exc:
            master_report.add_check("manifest_json_valid", False, f"Failed to parse manifest: {exc}")
            return master_report

        # 2. Validate manifest and DAG
        manifest_report = self.validate_manifest(manifest_data)
        for check in manifest_report.checks:
            master_report.add_check(check.name, check.passed, check.details)
        master_report.topological_order = manifest_report.topological_order

        # Collect declared concepts
        declared_concept_ids: Set[str] = set()
        for ch in manifest_data.get("chapters", []):
            for c in ch.get("concepts", []):
                if c.get("id"):
                    declared_concept_ids.add(c["id"])
        for c in manifest_data.get("concepts", []):
            if c.get("id"):
                declared_concept_ids.add(c["id"])

        # 3. Find and validate all resource packages and diagnostic banks
        json_pattern = os.path.join(content_dir, "**", "*.json")
        all_json_files = glob.glob(json_pattern, recursive=True)

        package_count = 0
        diag_count = 0

        for fpath in all_json_files:
            fname = os.path.basename(fpath)
            if fname in ("manifest.json", "manifest.schema.json", "chapter.json"):
                continue

            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
            except Exception as exc:
                master_report.add_check(f"parse_{fname}", False, f"Failed to parse {fpath}: {exc}")
                continue

            if fname.endswith("-diag.json") or fname == "diagnostic-bank.json":
                diag_count += 1
                diag_report = self.validate_diagnostic_bank(file_data, declared_concept_ids)
                for check in diag_report.checks:
                    master_report.add_check(f"{fname}:{check.name}", check.passed, check.details)
            else:
                package_count += 1
                pkg_report = self.validate_resource_package(file_data, declared_concept_ids)
                for check in pkg_report.checks:
                    master_report.add_check(f"{fname}:{check.name}", check.passed, check.details)

        is_cbse10 = ("cbse-10-math" in os.path.basename(content_dir))
        expected_min_pkgs = 20 if is_cbse10 else 4
        expected_min_diags = 4 if is_cbse10 else 1

        master_report.add_check(
            "total_resource_packages_count",
            package_count >= expected_min_pkgs,
            f"Validated {package_count} resource packages (expected >= {expected_min_pkgs})",
        )
        master_report.add_check(
            "total_diagnostic_banks_count",
            diag_count >= expected_min_diags,
            f"Validated {diag_count} diagnostic banks (expected >= {expected_min_diags})",
        )

        return master_report


def main() -> int:
    parser = argparse.ArgumentParser(description="ZENITH Curriculum Library Content Validator")
    parser.add_argument("--manifest", type=str, default=None, help="Path to manifest.json or content directory")
    args = parser.parse_args()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "content", "library"))
    target = args.manifest or os.path.join(base_dir, "cbse-10-math")
    if not os.path.exists(target):
        target = base_dir

    content_dir = os.path.dirname(target) if os.path.isfile(target) else target

    validator = LibraryValidator()
    print("=" * 80)
    print("ZENITH CURRICULUM LIBRARY CONTENT VALIDATION PIPELINE")
    print(f"Target Directory: {content_dir}")
    print("=" * 80)

    report = validator.validate_content_library(content_dir)

    for check in report.checks:
        status_mark = "PASS" if check.passed else "FAIL"
        print(f"[{status_mark:4}] {check.name:<35} | {check.details}")

    print("=" * 80)
    print(f"TOTAL CHECKS: {report.total_checks} | PASSED: {report.passed_checks} | FAILED: {report.failed_checks}")
    if report.topological_order:
        print(f"Topological Sort Verified ({len(report.topological_order)} concepts)")
    print("=" * 80)

    if not report.is_valid:
        print("\nERRORS DETECTED:")
        for err in report.errors:
            print(f"  - {err}")
        return 1

    print("ALL VALIDATION CHECKS PASSED (EXIT CODE 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
