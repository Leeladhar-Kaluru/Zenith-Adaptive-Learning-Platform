"""Idempotent Curriculum Library Database Seeder for SETU.

Seeds CBSE Class 10 Mathematics curriculum under immutable system owner:
SYSTEM_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

Populates:
- curriculum_boards, subjects, languages (foundations)
- concepts (25 nodes with canonical BKT parameters)
- concept_edges (22 DAG prerequisite dependencies)
- learning_paths (4 flagship chapters with is_library=True, library_slug)
- concept_chapters (links concepts to chapters with sequencing)
- path_lessons (20 resource packages)
- lesson_versions (version 1 containing full lesson_package_json)
- questions (practice & checkpoint questions indexed into questions table)
- library_publication_events (audit event with SHA-256 manifest hash)

CLI Callable:
python -m app.services.library_seed [--manifest PATH] [--validate-only] [--force]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.services.library_validator import LibraryValidator, ValidationReport

SYSTEM_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class LibrarySeeder:
    """Ingestion engine for curriculum library content into PostgreSQL."""

    def __init__(self, manifest_path: Optional[str] = None):
        self.manifest_path = manifest_path or self._resolve_manifest_path()
        self.content_dir = os.path.dirname(self.manifest_path)
        self.validator = LibraryValidator()

    def _resolve_manifest_path(self) -> str:
        candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "content", "library", "cbse-10-math", "manifest.json")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "content", "library", "manifest.json")),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return candidates[0]

    def validate_only(self) -> ValidationReport:
        """Runs library validation without database writes."""
        return self.validator.validate_content_library(self.content_dir)

    def compute_manifest_hash(self) -> str:
        with open(self.manifest_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def seed(self, db_session: Any, force: bool = False) -> Dict[str, int]:
        """Performs idempotent seeding under system owner.
        
        Returns dict with counts of seeded entities.
        """
        # 1. Validation phase
        if not force:
            report = self.validate_only()
            if not report.is_valid:
                error_summary = "; ".join(report.errors[:3])
                raise ValueError(f"Content validation failed: {error_summary}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        manifest_hash = self.compute_manifest_hash()

        # Late imports of SQLAlchemy models to allow validate-only without DB dependencies
        from app.models.curriculum import CurriculumBoard, Subject, Language
        from app.models.library import Concept, ConceptEdge, ConceptChapter, LibraryPublicationEvent
        from app.models.learning import LearningPath, PathLesson, LessonVersion, Question

        counts = {
            "boards": 0,
            "subjects": 0,
            "languages": 0,
            "concepts": 0,
            "concept_edges": 0,
            "chapters": 0,
            "concept_chapters": 0,
            "path_lessons": 0,
            "lesson_versions": 0,
            "questions": 0,
            "events": 0,
        }

        # 2. Seed Foundation Lookup Tables
        # Board
        board = db_session.query(CurriculumBoard).filter_by(id="board-cbse").first()
        if not board:
            board = CurriculumBoard(
                id="board-cbse",
                code="CBSE",
                name="Central Board of Secondary Education",
                active=True,
            )
            db_session.add(board)
            counts["boards"] += 1

        # Subject
        subject = db_session.query(Subject).filter_by(id="subject-math").first()
        if not subject:
            subject = Subject(
                id="subject-math",
                code="MATH",
                canonical_name="Mathematics",
                active=True,
            )
            db_session.add(subject)
            counts["subjects"] += 1

        # Language
        lang = db_session.query(Language).filter_by(id="lang-en").first()
        if not lang:
            lang = Language(
                id="lang-en",
                bcp47_tag="en-IN",
                native_name="English (India)",
                script="Latn",
                active=True,
            )
            db_session.add(lang)
            counts["languages"] += 1

        db_session.flush()

        # 3. Seed Concepts (25 concepts)
        all_concepts: List[Dict[str, Any]] = []
        for ch in manifest_data.get("chapters", []):
            all_concepts.extend(ch.get("concepts", []))
        all_concepts.extend(manifest_data.get("concepts", []))

        # Deduplicate by concept id
        seen_concepts = set()
        unique_concepts = []
        for c in all_concepts:
            if c["id"] not in seen_concepts:
                seen_concepts.add(c["id"])
                unique_concepts.append(c)

        for c_data in unique_concepts:
            c_row = db_session.query(Concept).filter_by(id=c_data["id"]).first()
            if not c_row:
                c_row = Concept(id=c_data["id"])
                db_session.add(c_row)
                counts["concepts"] += 1

            c_row.slug = c_data.get("slug", c_data["id"])
            c_row.title = c_data["title"]
            c_row.description = c_data.get("description", "")
            c_row.grade = c_data.get("grade", 10)
            c_row.subject_id = c_data.get("subjectId", "subject-math")
            c_row.keywords = c_data.get("keywords", [])

            bkt = c_data.get("bktParams", {})
            c_row.p_l0 = bkt.get("pL0", 0.25)
            c_row.p_t = bkt.get("pT", 0.15)
            c_row.p_g = bkt.get("pG", 0.20)
            c_row.p_s = bkt.get("pS", 0.10)

        db_session.flush()

        # 4. Seed Concept Edges (22 edges)
        for edge in manifest_data.get("dagEdges", []):
            u = edge.get("fromConceptId") or edge.get("from")
            v = edge.get("toConceptId") or edge.get("to")
            e_row = db_session.query(ConceptEdge).filter_by(
                from_concept_id=u, to_concept_id=v
            ).first()
            if not e_row:
                e_row = ConceptEdge(
                    from_concept_id=u,
                    to_concept_id=v,
                )
                db_session.add(e_row)
                counts["concept_edges"] += 1
            e_row.relationship = edge.get("relationship", "prerequisite")
            e_row.weight = edge.get("weight", 1.0)

        db_session.flush()

        # 5. Seed Chapters (LearningPaths) & Resources (PathLessons)
        for ch in manifest_data.get("chapters", []):
            ch_slug = ch["slug"]
            path = (
                db_session.query(LearningPath)
                .filter(
                    LearningPath.is_library.is_(True),
                    LearningPath.library_slug == ch_slug,
                )
                .first()
            )
            if not path:
                path = LearningPath(
                    owner_id=SYSTEM_OWNER_ID,
                    is_library=True,
                    library_slug=ch_slug,
                )
                db_session.add(path)
                counts["chapters"] += 1

            path.grade = 10
            path.subject_id = "subject-math"
            path.board_id = "board-cbse"
            path.status = "active"
            path.library_status = "published"
            path.outline_json = {
                "title": ch["title"],
                "description": ch.get("description", ""),
                "chapterNumber": ch.get("chapterNumber", 1),
                "slug": ch_slug,
            }
            db_session.flush()

            # Link concepts to chapter (concept_chapters)
            for idx, concept_item in enumerate(ch.get("concepts", []), start=1):
                c_id = concept_item["id"]
                cc_link = (
                    db_session.query(ConceptChapter)
                    .filter_by(concept_id=c_id, path_id=path.id)
                    .first()
                )
                if not cc_link:
                    cc_link = ConceptChapter(
                        concept_id=c_id,
                        path_id=path.id,
                    )
                    db_session.add(cc_link)
                    counts["concept_chapters"] += 1
                cc_link.chapter_order = idx

            db_session.flush()

            # Seed Resources (5 per chapter)
            for res_meta in ch.get("resources", []):
                res_key = res_meta["key"]
                res_file = res_meta["file"]

                lesson = (
                    db_session.query(PathLesson)
                    .filter_by(path_id=path.id, lesson_key=res_key)
                    .first()
                )
                if not lesson:
                    lesson = PathLesson(
                        path_id=path.id,
                        lesson_key=res_key,
                    )
                    db_session.add(lesson)
                    counts["path_lessons"] += 1

                lesson.title = res_meta["title"]
                lesson.sequence = res_meta.get("sequence", 1)
                lesson.status = "ready"
                db_session.flush()

                # Load resource package JSON
                res_filepath = os.path.join(self.content_dir, res_file)
                if not os.path.exists(res_filepath):
                    res_filepath = os.path.join(self.content_dir, os.path.basename(res_file))

                if os.path.exists(res_filepath):
                    with open(res_filepath, "r", encoding="utf-8") as rf:
                        pkg_json = json.load(rf)

                    # Upsert LessonVersion
                    l_ver = (
                        db_session.query(LessonVersion)
                        .filter_by(path_lesson_id=lesson.id, version_number=1)
                        .first()
                    )
                    if not l_ver:
                        l_ver = LessonVersion(
                            path_lesson_id=lesson.id,
                            version_number=1,
                        )
                        db_session.add(l_ver)
                        counts["lesson_versions"] += 1

                    l_ver.lesson_package_json = pkg_json
                    l_ver.validation_status = "ready"
                    l_ver.estimated_bytes = len(json.dumps(pkg_json))
                    db_session.flush()

                    # Index questions into questions table
                    all_qs = (pkg_json.get("practice") or []) + (pkg_json.get("checkpointTest") or [])
                    for q in all_qs:
                        q_key = q.get("questionId") or q.get("id")
                        q_row = (
                            db_session.query(Question)
                            .filter_by(lesson_version_id=l_ver.id, question_key=q_key)
                            .first()
                        )
                        if not q_row:
                            q_row = Question(
                                lesson_version_id=l_ver.id,
                                question_key=q_key,
                            )
                            db_session.add(q_row)
                            counts["questions"] += 1

                        q_row.type = q.get("type", "multiple_choice")
                        q_row.prompt_json = {
                            "text": q.get("prompt") or q.get("text", ""),
                            "options": q.get("options", []),
                        }
                        q_row.answer_key_json = {
                            "answerKey": q.get("answerKey"),
                            "feedback": q.get("feedback", ""),
                            "hints": q.get("hints", []),
                        }
                        q_row.concept_ids = q.get("conceptIds") or ([q["conceptId"]] if "conceptId" in q else [])
                        q_row.difficulty = q.get("difficulty", "standard")
                        q_row.validation_status = "ready"

            # Record Publication Event
            event = LibraryPublicationEvent(
                path_id=path.id,
                publisher_id=SYSTEM_OWNER_ID,
                version_tag="1.0.0",
                manifest_hash=manifest_hash,
                changes_summary=f"Published CBSE Class 10 {ch['title']} curriculum packages",
            )
            db_session.add(event)
            counts["events"] += 1

        db_session.commit()
        return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="SETU Curriculum Library Idempotent Seeder")
    parser.add_argument("--manifest", type=str, default=None, help="Path to manifest.json")
    parser.add_argument("--validate-only", action="store_true", help="Run schema and DAG validation only without database writes")
    parser.add_argument("--force", action="store_true", help="Bypass validation during seeding")
    args = parser.parse_args()

    seeder = LibrarySeeder(manifest_path=args.manifest)

    print("=" * 80)
    print("SETU CURRICULUM LIBRARY SEEDER")
    print(f"Manifest: {seeder.manifest_path}")
    print("=" * 80)

    if args.validate_only:
        print("[MODE] VALIDATE ONLY (Zero Database Writes)")
        report = seeder.validate_only()
        for check in report.checks:
            mark = "PASS" if check.passed else "FAIL"
            print(f"[{mark:4}] {check.name:<35} | {check.details}")
        print("=" * 80)
        print(f"TOTAL CHECKS: {report.total_checks} | PASSED: {report.passed_checks} | FAILED: {report.failed_checks}")
        if not report.is_valid:
            print("VALIDATION FAILED (EXIT CODE 1)")
            return 1
        print("VALIDATION PASSED (EXIT CODE 0)")
        return 0

    # Live Database Seeding
    print("[MODE] LIVE DATABASE SEEDING (Idempotent Ingestion)")
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
    except Exception as exc:
        print(f"ERROR connecting to database: {exc}", file=sys.stderr)
        return 1

    try:
        counts = seeder.seed(db, force=args.force)
        print("=" * 80)
        print("DATABASE SEEDING SUCCESSFUL:")
        for k, v in counts.items():
            print(f"  - {k:<20}: {v}")
        print("=" * 80)
        print("ALL CURRICULUM ENTITIES SEEDED IDEMPOTENTLY (EXIT CODE 0)")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR during seeding: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
