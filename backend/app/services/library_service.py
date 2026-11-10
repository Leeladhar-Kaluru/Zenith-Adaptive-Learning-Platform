"""Curriculum Library Service for SETU.

Provides access to curriculum chapters, concepts, resource packages,
learning map DAGs, and progress tracking.
Implements a database-first strategy with self-healing fallback to
manifest and package JSONs in backend/app/content/library/cbse-10-math.
Guarantees student question redaction via package_redaction.py.
"""
from __future__ import annotations

import datetime
import json
import os
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.learning import LearningPath, PathLesson, LessonVersion
from app.models.library import (
    Concept,
    ConceptEdge,
    ConceptChapter,
    LibraryEnrollment,
    ResourceProgress,
)
from app.models.mastery import BktState
from app.services.package_redaction import redact_resource_package
from app.services.rewards_service import award_activity_rewards
from app.services.library_access import can_read_resource

LIBRARY_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "content",
    "library",
)
CONTENT_DIR = os.path.join(LIBRARY_BASE_DIR, "cbse-10-math")
MANIFEST_PATH = os.path.join(CONTENT_DIR, "manifest.json")


def _get_curriculum_dir(grade: Optional[int] = 10, subject_id: Optional[str] = "subject-math") -> str:
    if grade is None:
        grade = 10
    subj_code = "science" if "science" in str(subject_id or "").lower() or "sci" in str(subject_id or "").lower() else "math"
    dir_name = f"cbse-{int(grade):02d}-{subj_code}"
    target = os.path.join(LIBRARY_BASE_DIR, dir_name)
    if os.path.isdir(target):
        return target
    return CONTENT_DIR


def _load_manifest(grade: Optional[int] = None, subject_id: Optional[str] = None) -> Dict[str, Any]:
    """Loads manifest.json from library content directory."""
    if grade is not None:
        cur_dir = _get_curriculum_dir(grade, subject_id)
        m_path = os.path.join(cur_dir, "manifest.json")
        if os.path.exists(m_path):
            try:
                with open(m_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _load_all_manifests() -> List[Dict[str, Any]]:
    """Loads all manifests across all classes and subjects."""
    manifests = []
    if os.path.exists(LIBRARY_BASE_DIR):
        for entry in sorted(os.listdir(LIBRARY_BASE_DIR)):
            m_path = os.path.join(LIBRARY_BASE_DIR, entry, "manifest.json")
            if os.path.isfile(m_path):
                try:
                    with open(m_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data and "chapters" in data:
                            manifests.append(data)
                except Exception:
                    pass
    if not manifests:
        def_m = _load_manifest()
        if def_m:
            manifests.append(def_m)
    return manifests


def _load_package_file(file_name: str) -> Optional[Dict[str, Any]]:
    """Loads a specific resource package JSON from content directory."""
    candidates = [
        os.path.join(LIBRARY_BASE_DIR, file_name),
        os.path.join(CONTENT_DIR, file_name),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    bare_name = os.path.basename(file_name)
    if not bare_name.endswith(".json"):
        bare_name += ".json"

    if os.path.exists(LIBRARY_BASE_DIR):
        for sub in os.listdir(LIBRARY_BASE_DIR):
            sub_path = os.path.join(LIBRARY_BASE_DIR, sub)
            if os.path.isdir(sub_path):
                cand = os.path.join(sub_path, bare_name)
                if os.path.exists(cand) and os.path.isfile(cand):
                    try:
                        with open(cand, "r", encoding="utf-8") as f:
                            return json.load(f)
                    except Exception:
                        pass
    return None


def get_catalogue(
    db: Session,
    grade: int = 10,
    subject_id: str = "subject-math",
    user_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """Returns curriculum library catalogue with chapter metadata and enrollment status."""
    manifest = _load_manifest(grade=grade, subject_id=subject_id)
    board_data = manifest.get("board", {"id": "board-cbse", "code": "CBSE", "name": "Central Board of Secondary Education"})
    subject_data = manifest.get("subject", {
        "id": subject_id,
        "code": "SCI" if "science" in subject_id.lower() or "sci" in subject_id.lower() else "MATH",
        "name": "Science" if "science" in subject_id.lower() or "sci" in subject_id.lower() else "Mathematics",
    })

    # Check for enrolled chapters if user_id is provided
    enrolled_path_ids = set()
    if user_id is not None:
        try:
            enrollments = (
                db.query(LibraryEnrollment)
                .filter(LibraryEnrollment.student_id == user_id, LibraryEnrollment.status == "active")
                .all()
            )
            enrolled_path_ids = {e.path_id for e in enrollments}
        except Exception:
            pass

    # Fetch library paths from DB
    db_paths = (
        db.query(LearningPath)
        .filter(LearningPath.is_library.is_(True))
        .all()
    )
    db_path_by_slug = {p.library_slug: p for p in db_paths if p.library_slug}

    chapters_output = []
    manifest_chapters = manifest.get("chapters", [])

    for ch in manifest_chapters:
        slug = ch.get("slug")
        path_obj = db_path_by_slug.get(slug)
        is_enrolled = (path_obj.id in enrolled_path_ids) if path_obj else False

        # Calculate progress if enrolled
        completion_pct = 0.0
        if is_enrolled and path_obj and user_id:
            try:
                lesson_ids = [l.id for l in db.query(PathLesson).filter(PathLesson.path_id == path_obj.id).all()]
                if lesson_ids:
                    done_count = (
                        db.query(ResourceProgress)
                        .filter(
                            ResourceProgress.student_id == user_id,
                            ResourceProgress.path_lesson_id.in_(lesson_ids),
                            ResourceProgress.status == "completed",
                        )
                        .count()
                    )
                    completion_pct = round((done_count / float(len(lesson_ids))) * 100.0, 1)
            except Exception:
                pass

        chapters_output.append({
            "id": ch.get("id"),
            "slug": slug,
            "chapterNumber": ch.get("chapterNumber", 1),
            "title": ch.get("title", ""),
            "description": ch.get("description", ""),
            "conceptCount": len(ch.get("concepts", [])),
            "resourceCount": len(ch.get("resources", [])),
            "estimatedMinutes": sum(r.get("estimatedMinutes", 20) for r in ch.get("resources", [])),
            "isEnrolled": is_enrolled,
            "completionPct": completion_pct,
        })

    return {
        "curriculumId": manifest.get("curriculumId", f"cbse-{grade:02d}-{subject_data.get('code', 'math').lower()}"),
        "board": board_data,
        "boards": ["cbse"],
        "grade": grade,
        "grades": [6, 7, 8, 9, 10],
        "subject": subject_data,
        "subjects": ["subject-math", "subject-science"],
        "totalChapters": len(chapters_output),
        "totalConcepts": sum(c["conceptCount"] for c in chapters_output),
        "totalLessons": sum(c["resourceCount"] for c in chapters_output),
        "chapters": chapters_output,
    }


def get_chapter(
    db: Session,
    chapter_slug: str,
    user_id: Optional[uuid.UUID] = None,
) -> Optional[Dict[str, Any]]:
    """Fetches details for a single chapter, searching across all grades and subjects."""
    clean_slug = chapter_slug
    for pfx in ["cbse-10-math-", "cbse-06-math-", "cbse-07-math-", "cbse-08-math-", "cbse-09-math-", "cbse-10-science-"]:
        clean_slug = clean_slug.replace(pfx, "")

    all_manifests = _load_all_manifests()
    target_ch = None
    parent_manifest: Dict[str, Any] = {}

    for m in all_manifests:
        for ch in m.get("chapters", []):
            if (
                ch.get("slug") == clean_slug
                or ch.get("id") == clean_slug
                or ch.get("slug") == chapter_slug
                or ch.get("id") == chapter_slug
            ):
                target_ch = ch
                parent_manifest = m
                break
        if target_ch:
            break

    if not target_ch:
        return None

    ch_grade = target_ch.get("grade") or parent_manifest.get("grade", 10)
    ch_subj = target_ch.get("subjectId") or (parent_manifest.get("subject") or {}).get("id", "subject-math")

    # Concepts in chapter
    concepts = []
    for c in target_ch.get("concepts", []):
        bkt_params = c.get("bktParams", {})
        concepts.append({
            "id": c.get("id"),
            "slug": c.get("slug", ""),
            "title": c.get("title", ""),
            "description": c.get("description", ""),
            "grade": c.get("grade", ch_grade),
            "order": c.get("order", 1),
            "pL0": bkt_params.get("pL0", 0.25),
            "pT": bkt_params.get("pT", 0.15),
            "pG": bkt_params.get("pG", 0.20),
            "pS": bkt_params.get("pS", 0.10),
        })

    # Resources in chapter
    resources = []
    path = (
        db.query(LearningPath)
        .filter(LearningPath.is_library.is_(True), LearningPath.library_slug == clean_slug)
        .first()
    )
    db_lessons = []
    if path:
        db_lessons = (
            db.query(PathLesson)
            .filter(PathLesson.path_id == path.id)
            .order_by(PathLesson.sequence.asc())
            .all()
        )

    db_lesson_map = {l.lesson_key: l for l in db_lessons}

    for r in target_ch.get("resources", []):
        lesson_key = r.get("key") or r.get("lessonKey") or r.get("lessonId") or r.get("id")
        db_lesson = db_lesson_map.get(lesson_key)
        res_id = str(db_lesson.id) if db_lesson else lesson_key

        resources.append({
            "id": res_id,
            "lessonKey": lesson_key,
            "resourceKind": r.get("resourceKind", "lesson"),
            "title": r.get("title", ""),
            "sequence": r.get("sequence", 1),
            "estimatedMinutes": r.get("estimatedMinutes", 20),
            "status": "ready",
            "file": r.get("file", ""),
        })

    chapter_meta = {
        "id": target_ch.get("id"),
        "slug": clean_slug,
        "chapterNumber": target_ch.get("chapterNumber", 1),
        "title": target_ch.get("title", ""),
        "description": target_ch.get("description", ""),
        "grade": ch_grade,
        "subjectId": ch_subj,
        "boardId": "board-cbse",
    }
    return {
        **chapter_meta,
        "chapter": chapter_meta,
        "concepts": concepts,
        "resources": resources,
    }


def get_resource(
    db: Session,
    resource_id: str,
    student_id: Optional[uuid.UUID] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieves a resource package by UUID or lesson key, with safe student redaction."""
    # 1. Try DB lookup
    package_data = None
    lesson_key = resource_id
    lesson_title = ""
    sequence = 1
    path_lesson = None

    try:
        res_uuid = uuid.UUID(resource_id)
        path_lesson = db.query(PathLesson).filter(PathLesson.id == res_uuid).first()
    except Exception:
        path_lesson = db.query(PathLesson).filter(PathLesson.lesson_key == resource_id).first()

    if path_lesson is not None:
        if not can_read_resource(path_lesson, student_id, db):
            return None
        lesson_key = path_lesson.lesson_key
        lesson_title = path_lesson.title
        sequence = path_lesson.sequence
        version = (
            db.query(LessonVersion)
            .filter(LessonVersion.path_lesson_id == path_lesson.id)
            .order_by(LessonVersion.version_number.desc())
            .first()
        )
        if version and version.lesson_package_json:
            package_data = version.lesson_package_json

        # Upsert in_progress status for student
        if student_id is not None:
            try:
                progress = (
                    db.query(ResourceProgress)
                    .filter(
                        ResourceProgress.student_id == student_id,
                        ResourceProgress.path_lesson_id == path_lesson.id,
                    )
                    .first()
                )
                if progress is None:
                    progress = ResourceProgress(
                        id=uuid.uuid4(),
                        student_id=student_id,
                        path_lesson_id=path_lesson.id,
                        status="in_progress",
                        completion_pct=0.0,
                        time_spent_seconds=0,
                        updated_at=datetime.datetime.utcnow(),
                    )
                    db.add(progress)
                    db.flush()
            except Exception:
                pass

    # 2. If DB had no package data, fallback to JSON files
    if package_data is None:
        all_manifests = _load_all_manifests()
        for manifest in all_manifests:
            for ch in manifest.get("chapters", []):
                for r in ch.get("resources", []):
                    r_file = r.get("file", "")
                    r_base = os.path.basename(r_file).replace(".json", "")
                    if (
                        r.get("key") == lesson_key
                        or r.get("lessonKey") == lesson_key
                        or r.get("lessonId") == lesson_key
                        or r.get("id") == lesson_key
                        or r_file.replace(".json", "") == lesson_key
                        or r_base == lesson_key
                    ):
                        lesson_title = r.get("title", "")
                        sequence = r.get("sequence", 1)
                        package_data = _load_package_file(r_file or f"{lesson_key}.json")
                        break
                if package_data is not None:
                    break
            if package_data is not None:
                break

    if package_data is None:
        # Direct file check
        package_data = _load_package_file(f"{resource_id}.json")
        if package_data:
            lesson_title = package_data.get("title", "")
            lesson_key = package_data.get("lessonId", resource_id)

    if package_data is None:
        return None

    # Redact practice/checkpoint items for student safety while preserving worked examples and blocks
    sanitized_package = redact_resource_package(package_data)

    res_uuid_or_key = str(path_lesson.id) if path_lesson else resource_id
    return {
        "id": res_uuid_or_key,
        "resourceId": res_uuid_or_key,
        "lessonKey": lesson_key,
        "title": lesson_title or sanitized_package.get("title", ""),
        "sequence": sequence,
        "package": sanitized_package,
    }


def get_concept_map(
    db: Session,
    chapter_slug: str,
    student_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """Returns concept DAG nodes and edges for SVG map rendering."""
    clean_slug = chapter_slug
    for pfx in ["cbse-10-math-", "cbse-06-math-", "cbse-07-math-", "cbse-08-math-", "cbse-09-math-", "cbse-10-science-"]:
        clean_slug = clean_slug.replace(pfx, "")

    all_manifests = _load_all_manifests()
    target_ch = None
    target_manifest: Dict[str, Any] = {}

    for m in all_manifests:
        for ch in m.get("chapters", []):
            if (
                ch.get("slug") == clean_slug
                or ch.get("id") == clean_slug
                or ch.get("slug") == chapter_slug
                or ch.get("id") == chapter_slug
            ):
                target_ch = ch
                target_manifest = m
                break
        if target_ch:
            break

    if not target_ch:
        return {"nodes": [], "edges": []}

    ch_grade = target_ch.get("grade") or target_manifest.get("grade", 10)
    concept_ids = [c["id"] for c in target_ch.get("concepts", [])]

    # Fetch student BKT states if student_id is provided
    bkt_states: Dict[str, BktState] = {}
    if student_id is not None:
        try:
            states = (
                db.query(BktState)
                .filter(
                    BktState.student_id == student_id,
                    BktState.concept_id.in_(concept_ids),
                )
                .all()
            )
            bkt_states = {s.concept_id: s for s in states}
        except Exception:
            pass

    nodes = []
    for c in target_ch.get("concepts", []):
        cid = c["id"]
        state = bkt_states.get(cid)
        p_know = state.p_know if state else 0.25
        band = state.mastery_band if state else "not_started"
        is_gap = state.is_gap if state else False

        nodes.append({
            "id": cid,
            "title": c.get("title", cid),
            "description": c.get("description", ""),
            "grade": c.get("grade", ch_grade),
            "order": c.get("order", 1),
            "pKnow": p_know,
            "masteryBand": band,
            "isGap": is_gap,
        })

    # Filter edges where both concepts are in this chapter or related
    edges = []
    manifest_edges = target_manifest.get("dagEdges", [])
    c_set = set(concept_ids)

    for edge in manifest_edges:
        f_id = edge.get("fromConceptId")
        t_id = edge.get("toConceptId")
        if f_id in c_set or t_id in c_set:
            edges.append({
                "from": f_id,
                "to": t_id,
                "relationship": edge.get("relationship", "prerequisite"),
                "weight": edge.get("weight", 1.0),
            })

    return {
        "chapterSlug": clean_slug,
        "nodes": nodes,
        "edges": edges,
    }


def enroll_student(
    db: Session,
    student_id: uuid.UUID,
    chapter_slug: str,
) -> Dict[str, Any]:
    """Enrolls student in a curriculum library chapter."""
    clean_slug = chapter_slug.replace("cbse-10-math-", "")
    path = (
        db.query(LearningPath)
        .filter(LearningPath.is_library.is_(True), LearningPath.library_slug == clean_slug)
        .first()
    )
    if not path:
        # Create self-healing path record
        path = LearningPath(
            id=uuid.uuid4(),
            owner_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            grade=10,
            subject_id="subject-math",
            is_library=True,
            library_slug=clean_slug,
            library_status="published",
            outline_json={"title": clean_slug.replace("-", " ").title()},
            created_at=datetime.datetime.utcnow(),
        )
        db.add(path)
        db.flush()

    enrollment = (
        db.query(LibraryEnrollment)
        .filter(
            LibraryEnrollment.student_id == student_id,
            LibraryEnrollment.path_id == path.id,
        )
        .first()
    )
    if enrollment is None:
        enrollment = LibraryEnrollment(
            id=uuid.uuid4(),
            student_id=student_id,
            path_id=path.id,
            status="active",
            enrolled_at=datetime.datetime.utcnow(),
            last_accessed_at=datetime.datetime.utcnow(),
        )
        db.add(enrollment)
    else:
        enrollment.status = "active"
        enrollment.last_accessed_at = datetime.datetime.utcnow()

    db.flush()
    return {
        "enrolled": True,
        "chapterSlug": clean_slug,
        "pathId": str(path.id),
        "status": enrollment.status,
    }


def get_student_learning(db: Session, student_id: uuid.UUID) -> Dict[str, Any]:
    """Returns active enrollments and progress for the current student."""
    enrollments = (
        db.query(LibraryEnrollment, LearningPath)
        .join(LearningPath, LibraryEnrollment.path_id == LearningPath.id)
        .filter(LibraryEnrollment.student_id == student_id, LibraryEnrollment.status == "active")
        .all()
    )

    enrolled_chapters = []
    for enr, lp in enrollments:
        slug = lp.library_slug or "chapter"
        enrolled_chapters.append({
            "pathId": str(lp.id),
            "chapterSlug": slug,
            "title": (lp.outline_json or {}).get("title", slug.replace("-", " ").title()),
            "enrolledAt": enr.enrolled_at.isoformat() if enr.enrolled_at else None,
            "lastAccessedAt": enr.last_accessed_at.isoformat() if enr.last_accessed_at else None,
        })

    completed_resources_count = (
        db.query(ResourceProgress)
        .filter(ResourceProgress.student_id == student_id, ResourceProgress.status == "completed")
        .count()
    )

    return {
        "studentId": str(student_id),
        "totalEnrolledChapters": len(enrolled_chapters),
        "totalCompletedResources": completed_resources_count,
        "enrolledChapters": enrolled_chapters,
    }


def update_resource_progress(
    db: Session,
    student_id: uuid.UUID,
    path_lesson_id: str,
    status: str = "in_progress",
    completion_pct: float = 0.0,
    time_spent_seconds: int = 0,
    last_position: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Updates progress on a lesson resource and awards rewards upon completion."""
    path_lesson = None
    try:
        target_uuid = uuid.UUID(path_lesson_id)
        path_lesson = db.query(PathLesson).filter(PathLesson.id == target_uuid).first()
    except Exception:
        path_lesson = db.query(PathLesson).filter(PathLesson.lesson_key == path_lesson_id).first()

    if path_lesson is None or not can_read_resource(path_lesson, student_id, db):
        return None

    target_uuid = path_lesson.id
    rewards_awarded = None

    if target_uuid is not None:
        progress = (
            db.query(ResourceProgress)
            .filter(
                ResourceProgress.student_id == student_id,
                ResourceProgress.path_lesson_id == target_uuid,
            )
            .first()
        )
        if progress is None:
            progress = ResourceProgress(
                id=uuid.uuid4(),
                student_id=student_id,
                path_lesson_id=target_uuid,
                status=status,
                completion_pct=completion_pct,
                time_spent_seconds=time_spent_seconds,
                last_position_json=last_position or {},
                updated_at=datetime.datetime.utcnow(),
            )
            db.add(progress)
        else:
            progress.status = status
            progress.completion_pct = max(progress.completion_pct, completion_pct)
            progress.time_spent_seconds += time_spent_seconds
            if last_position:
                progress.last_position_json = last_position
            progress.updated_at = datetime.datetime.utcnow()

        # If completed, award activity rewards
        if status == "completed" or completion_pct >= 100.0:
            rewards_awarded = award_activity_rewards(
                db=db,
                student_id=student_id,
                event_type="resource_completed",
                idempotency_key=f"resource:{target_uuid}:{student_id}",
                xp_amount=20,
                coins_amount=5,
            )

        db.flush()

    return {
        "status": status,
        "completionPct": completion_pct,
        "rewardsAwarded": rewards_awarded,
    }
