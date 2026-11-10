"""Adaptive Practice Arena Service for ZENITH.

Selects calibrated problems, evaluates student submissions deterministically,
updates BKT mastery probabilities, and awards gamification rewards.
Zero LLM calls for mastery tracking and grading (Requirement 11).
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import String
from sqlalchemy.orm import Session

from app.models.learning import LearningPath, PathLesson, LessonVersion, Question, QuizAttempt, ConceptEvidence
from app.models.mastery import BktState
from app.models.library import Concept, ConceptChapter
from app.services.package_redaction import redact_single_question_for_student
from app.services.bkt import record_bkt_observation, get_or_create_bkt_state
from app.services.rewards_service import award_activity_rewards

logger = logging.getLogger(__name__)

LIBRARY_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "content",
    "library",
)
CONTENT_DIR = os.path.join(LIBRARY_BASE_DIR, "cbse-10-math")


def _load_manifest_concepts_for_chapter(clean_slug: str) -> List[Dict[str, Any]]:
    """Loads chapter concepts from all manifests in content library."""
    manifest_files = []
    if os.path.exists(LIBRARY_BASE_DIR):
        for entry in os.listdir(LIBRARY_BASE_DIR):
            cand = os.path.join(LIBRARY_BASE_DIR, entry, "manifest.json")
            if os.path.isfile(cand):
                manifest_files.append(cand)
    if not manifest_files:
        manifest_files = [os.path.join(CONTENT_DIR, "manifest.json")]

    for m_path in manifest_files:
        try:
            with open(m_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for ch in data.get("chapters", []):
                if (
                    ch.get("slug") == clean_slug
                    or ch.get("id") == clean_slug
                    or clean_slug in ch.get("slug", "")
                    or clean_slug in ch.get("id", "")
                ):
                    return ch.get("concepts", [])
        except Exception:
            pass
    return []


def get_practice_recommendation(
    db: Session,
    student_id: uuid.UUID,
    chapter_slug: str,
) -> Dict[str, Any]:
    """Recommends the highest-priority concept for practice.
    
    Priority:
    1. Confirmed prerequisite gap (`is_gap == True`).
    2. Lowest mastery probability ($P(know) < 0.60$).
    3. Unattempted concept ($N == 0$).
    4. Concept with oldest activity timestamp.
    """
    clean_slug = chapter_slug
    for pfx in ["cbse-10-math-", "cbse-06-math-", "cbse-07-math-", "cbse-08-math-", "cbse-09-math-", "cbse-10-science-"]:
        clean_slug = clean_slug.replace(pfx, "")
    
    # 1. Gather concepts for this chapter from DB
    concepts = []
    path = (
        db.query(LearningPath)
        .filter(LearningPath.is_library.is_(True), LearningPath.library_slug == clean_slug)
        .first()
    )
    if path:
        c_links = (
            db.query(ConceptChapter, Concept)
            .join(Concept, ConceptChapter.concept_id == Concept.id)
            .filter(ConceptChapter.path_id == path.id)
            .all()
        )
        concepts = [{"id": c.id, "title": c.title, "grade": c.grade} for _, c in c_links]

    if not concepts:
        # Fallback to manifest
        m_concepts = _load_manifest_concepts_for_chapter(clean_slug)
        concepts = [{"id": c["id"], "title": c.get("title", c["id"]), "grade": c.get("grade", 10)} for c in m_concepts]

    if not concepts:
        return {
            "conceptId": None,
            "conceptTitle": "General Practice",
            "pKnow": 0.25,
            "masteryBand": "not_started",
            "isGap": False,
            "reason": "No specific concepts registered for this chapter.",
        }

    concept_ids = [c["id"] for c in concepts]
    bkt_states = {
        s.concept_id: s
        for s in db.query(BktState).filter(
            BktState.student_id == student_id,
            BktState.concept_id.in_(concept_ids),
        ).all()
    }

    # Score each concept for practice urgency
    candidates = []
    for c in concepts:
        cid = c["id"]
        state = bkt_states.get(cid)
        p_know = state.p_know if state else 0.25
        is_gap = state.is_gap if state else False
        total_ops = state.total_opportunities if state else 0
        band = state.mastery_band if state else "not_started"

        # Determine priority category and reason
        if is_gap:
            rank = 1
            reason = f"Prerequisite gap detected in '{c['title']}'. Strengthen foundation."
        elif p_know < 0.60:
            rank = 2
            reason = f"Low mastery ({int(p_know * 100)}%) in '{c['title']}'. Build proficiency."
        elif total_ops == 0:
            rank = 3
            reason = f"Unattempted topic '{c['title']}'. Start initial practice."
        else:
            rank = 4
            reason = f"Review '{c['title']}' to maintain mastery."

        candidates.append({
            "conceptId": cid,
            "conceptTitle": c["title"],
            "grade": c["grade"],
            "pKnow": p_know,
            "masteryBand": band,
            "isGap": is_gap,
            "rank": rank,
            "reason": reason,
        })

    # Sort by rank ascending, then p_know ascending
    candidates.sort(key=lambda x: (x["rank"], x["pKnow"]))
    recommended = candidates[0]
    return {
        "conceptId": recommended["conceptId"],
        "conceptTitle": recommended["conceptTitle"],
        "pKnow": recommended["pKnow"],
        "masteryBand": recommended["masteryBand"],
        "isGap": recommended["isGap"],
        "reason": recommended["reason"],
    }


def _load_questions_from_content_dir(clean_slug: str, target_concept_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads practice questions directly from lesson JSON files across all curriculum folders."""
    questions = []
    if not os.path.exists(LIBRARY_BASE_DIR):
        return questions

    key_stem = clean_slug.split("-")[0]

    # Search all lesson and diagnostic JSON files across all subdirectories
    for root, _, files in os.walk(LIBRARY_BASE_DIR):
        for fname in files:
            if not fname.endswith(".json") or fname == "manifest.json":
                continue
            if clean_slug in fname or key_stem in fname or clean_slug in root:
                try:
                    with open(os.path.join(root, fname), "r", encoding="utf-8") as f:
                        pkg = json.load(f)
                    items_to_check = pkg.get("practice", [])
                    if fname.endswith("-diag.json"):
                        items_to_check = pkg.get("items", [])
                    for q in items_to_check:
                        cids = list(q.get("conceptIds", []))
                        if "conceptId" in q:
                            cids.append(q["conceptId"])
                        if target_concept_id is None or target_concept_id in cids:
                            questions.append(q)
                except Exception:
                    pass

    # 2. If no questions matched the target concept, fall back to any available questions from the chapter
    if not questions and target_concept_id is not None:
        return _load_questions_from_content_dir(clean_slug, target_concept_id=None)

    return questions


def get_practice_questions(
    db: Session,
    student_id: uuid.UUID,
    chapter_slug: str,
    concept_id: Optional[str] = None,
    count: int = 5,
) -> List[Dict[str, Any]]:
    """Draws calibrated, redacted practice questions for a student sitting."""
    clean_slug = chapter_slug.replace("cbse-10-math-", "")

    # Target concept recommendation if not explicitly passed
    if not concept_id:
        rec = get_practice_recommendation(db, student_id, clean_slug)
        concept_id = rec.get("conceptId")

    # 1. Query DB questions matching concept
    db_questions = []
    if concept_id:
        try:
            # Query questions where concept_ids JSON array contains concept_id
            db_questions = (
                db.query(Question)
                .filter(Question.concept_ids.cast(String).like(f"%{concept_id}%"))
                .limit(count * 2)
                .all()
            )
        except Exception as exc:
            logger.warning("Failed querying DB questions for concept %s: %s", concept_id, exc)

    # 2. Exclude questions student has already solved correctly
    solved_q_ids = set()
    try:
        solved_attempts = (
            db.query(QuizAttempt.question_id)
            .filter(QuizAttempt.owner_id == student_id, QuizAttempt.is_correct.is_(True))
            .all()
        )
        solved_q_ids = {str(a[0]) for a in solved_attempts}
    except Exception as exc:
        logger.warning("Failed querying solved attempts for student %s: %s", student_id, exc)

    available_items = []
    for q in db_questions:
        if str(q.id) not in solved_q_ids:
            prompt_data = q.prompt_json or {}
            item_payload = {
                "questionId": str(q.id),
                "conceptId": concept_id,
                "type": q.type,
                "prompt": prompt_data.get("prompt") or prompt_data.get("text", ""),
                "options": prompt_data.get("options", []),
                "difficulty": q.difficulty or "standard",
                "hints": prompt_data.get("hints", []),
            }
            available_items.append(item_payload)

    # 3. If DB didn't yield enough, fallback to content JSON files
    if len(available_items) < count:
        file_questions = _load_questions_from_content_dir(clean_slug, concept_id)
        for fq in file_questions:
            qid = fq.get("questionId") or fq.get("id") or "q-practice"
            if qid not in solved_q_ids and not any(it["questionId"] == qid for it in available_items):
                redacted = redact_single_question_for_student(fq)
                redacted["conceptId"] = concept_id
                available_items.append(redacted)
            if len(available_items) >= count:
                break

    # Redact all returned questions to guarantee zero answerKey leaks
    return [redact_single_question_for_student(it) for it in available_items[:count]]


def submit_practice_attempt(
    db: Session,
    student_id: uuid.UUID,
    question_id: str,
    concept_id: str,
    response: Any,
    hint_level: int = 0,
    hints_used: Optional[List[str]] = None,
    elapsed_seconds: int = 0,
    sync_idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Deterministically grades a practice attempt, updates BKT, and awards XP/coins."""
    # Check idempotency
    idempotency_key = sync_idempotency_key or f"practice:{student_id}:{question_id}:{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # 1. Try to find Question in DB
    db_question = None
    try:
        q_uuid = uuid.UUID(question_id)
        db_question = db.query(Question).filter(Question.id == q_uuid).first()
    except Exception:
        # Question id is a string key like "q-rn-ps-1"
        db_question = db.query(Question).filter(Question.question_key == question_id).first()

    # 2. Resolve expected answer & explanation
    expected_answer = None
    explanation = ""
    q_type = "multiple_choice"
    options = []
    lesson_version_id = None

    if db_question is not None:
        lesson_version_id = db_question.lesson_version_id
        q_type = db_question.type
        options = (db_question.prompt_json or {}).get("options", [])
        ak = db_question.answer_key_json or {}
        expected_answer = ak.get("answerKey") if "answerKey" in ak else ak.get("answer")
        explanation = ak.get("explanation") or ak.get("feedback") or ""
    else:
        # Search content files for the question
        found_q = None
        if os.path.exists(CONTENT_DIR):
            for fname in os.listdir(CONTENT_DIR):
                if fname.endswith(".json") and fname != "manifest.json":
                    with open(os.path.join(CONTENT_DIR, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for item in data.get("practice", []) + data.get("items", []):
                        if item.get("questionId") == question_id or item.get("id") == question_id:
                            found_q = item
                            break
                    if found_q:
                        break
        if found_q:
            q_type = found_q.get("type", "multiple_choice")
            options = found_q.get("options", [])
            expected_answer = found_q.get("answerKey") if "answerKey" in found_q else found_q.get("answer")
            explanation = found_q.get("explanation", "")

    # Grade response
    is_correct = False
    if expected_answer is not None:
        if q_type == "multiple_choice":
            if str(response).strip().lower() == str(expected_answer).strip().lower():
                is_correct = True
            elif isinstance(expected_answer, int) and 0 <= expected_answer < len(options):
                if str(response).strip().lower() == str(options[expected_answer]).strip().lower():
                    is_correct = True
            elif isinstance(response, int) and 0 <= response < len(options):
                if str(options[response]).strip().lower() == str(expected_answer).strip().lower():
                    is_correct = True
        elif q_type == "numeric":
            try:
                v1 = float(str(response).strip().replace(",", ""))
                v2 = float(str(expected_answer).strip().replace(",", ""))
                is_correct = abs(v1 - v2) <= max(1e-6, abs(v2) * 0.001)
            except Exception:
                is_correct = False
        else:
            is_correct = str(response).strip().lower() == str(expected_answer).strip().lower()

    attempt_id = uuid.uuid4()
    hints_count = len(hints_used or []) + (1 if hint_level > 0 else 0)
    hint_bool = hints_count > 0

    # 3. Update BKT State
    bkt_res = record_bkt_observation(
        db=db,
        student_id=student_id,
        concept_id=concept_id,
        is_correct=is_correct,
        hint_used=hint_bool,
        attempt_id=attempt_id,
    )

    # 4. Insert QuizAttempt & ConceptEvidence if lesson_version exists
    if lesson_version_id is not None and db_question is not None:
        try:
            attempt = QuizAttempt(
                id=attempt_id,
                owner_id=student_id,
                question_id=db_question.id,
                lesson_version_id=lesson_version_id,
                response_json={"response": response},
                score=1.0 if is_correct else 0.0,
                is_correct=is_correct,
                hint_level=hint_level,
                hints_used=hints_used or [],
                elapsed_seconds=elapsed_seconds,
                feedback_json={"explanation": explanation},
                sync_idempotency_key=idempotency_key,
                attempt_kind="practice",
                occurred_at=datetime.datetime.utcnow(),
            )
            db.add(attempt)

            evidence = ConceptEvidence(
                id=uuid.uuid4(),
                owner_id=student_id,
                concept_id=concept_id,
                source_attempt_id=attempt.id,
                evidence_type="practice_attempt",
                outcome="correct" if is_correct else "incorrect",
                weight=1.0,
                hints_used=hints_count,
                occurred_at=datetime.datetime.utcnow(),
            )
            db.add(evidence)
        except Exception:
            pass

    # 5. Award Rewards
    rewards_res = award_activity_rewards(
        db=db,
        student_id=student_id,
        event_type="practice",
        idempotency_key=f"attempt:{attempt_id}",
        xp_amount=10 if is_correct else 5,
        coins_amount=2 if is_correct else 1,
        meta={"is_correct": is_correct, "concept_id": concept_id, "completed_attempt": True},
    )

    db.flush()

    feedback_text = (
        f"Correct! {explanation}".strip()
        if is_correct
        else f"Not quite. The correct answer is: {expected_answer}. {explanation}".strip()
    )

    return {
        "attemptId": str(attempt_id),
        "isCorrect": is_correct,
        "score": 1.0 if is_correct else 0.0,
        "correctAnswer": expected_answer,
        "feedback": feedback_text,
        "bkt": {
            "conceptId": concept_id,
            "priorPKnow": bkt_res.prior_p_know,
            "postPKnow": bkt_res.post_p_know,
            "masteryBand": bkt_res.mastery_band,
            "isGap": bkt_res.is_gap,
        },
        "rewards": {
            "xpAwarded": rewards_res["xpAwarded"],
            "coinsAwarded": rewards_res["coinsAwarded"],
            "totalXp": rewards_res["totalXp"],
            "currentStreak": rewards_res["currentStreak"],
        },
        "nextAction": {
            "action": "continue_practice",
            "title": "Next Practice Problem",
        },
    }
