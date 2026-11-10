"""Package and question redaction service for student payloads in SETU.

Strips answer keys, solutions, explanations, and steps from quiz and diagnostic questions
while strictly preserving educational worked examples, reading blocks, and visual specifications.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Set

QUESTION_STRIP_KEYS: Set[str] = {
    "answerKey",
    "answer_key",
    "correct_answer",
    "correctAnswer",
    "explanation",
    "solution",
    "steps",
    "feedback",
    "math_verification",
}

QUESTION_CONTAINER_KEYS: List[str] = [
    "practice",
    "checkpointTest",
    "questions",
    "items",
    "diagnostic_items",
]


def redact_single_question_for_student(question: Dict[str, Any]) -> Dict[str, Any]:
    """Redacts answerKey, correct_answer, explanation, and steps from a single question.
    
    Preserves questionId/question_id, type, prompt/text, options, hints, conceptIds, difficulty.
    Cleans rubric of answer or solution keys to prevent devtools leakage.
    """
    if not isinstance(question, dict):
        return question

    redacted = copy.deepcopy(question)
    for key in QUESTION_STRIP_KEYS:
        redacted.pop(key, None)

    # Clean rubric if present: do not allow answer leakage in rubric
    if "rubric" in redacted and isinstance(redacted["rubric"], dict):
        cleaned_rubric = {
            k: v for k, v in redacted["rubric"].items()
            if k not in ("answer", "solution", "expected", "criteria_answers", "math_verification")
        }
        redacted["rubric"] = cleaned_rubric

    # Normalize question id and prompt text aliases for frontend consumers if needed
    if "questionId" in redacted and "question_id" not in redacted:
        redacted["question_id"] = redacted["questionId"]
    if "prompt" in redacted and "text" not in redacted:
        redacted["text"] = redacted["prompt"]

    return redacted


def redact_question_package_for_student(package_data: Dict[str, Any]) -> Dict[str, Any]:
    """Redacts student question payloads while strictly preserving educational reading sections,
    worked examples (which are pedagogical demonstrations and retain steps/answers), and visual specifications.
    Does not mutate the input dictionary in-place.
    """
    if not isinstance(package_data, dict):
        return package_data

    sanitized = copy.deepcopy(package_data)

    for container_key in QUESTION_CONTAINER_KEYS:
        items = sanitized.get(container_key)
        if isinstance(items, list):
            redacted_list: List[Any] = []
            for item in items:
                if isinstance(item, dict):
                    # Diagnostic items in DB often wrap question in question_json
                    if "question_json" in item and isinstance(item["question_json"], dict):
                        item_copy = copy.deepcopy(item)
                        item_copy["question_json"] = redact_single_question_for_student(item["question_json"])
                        item_copy.pop("student_response", None)
                        item_copy.pop("is_correct", None)
                        redacted_list.append(item_copy)
                    else:
                        redacted_list.append(redact_single_question_for_student(item))
                else:
                    redacted_list.append(item)
            sanitized[container_key] = redacted_list

    return sanitized


def redact_resource_package(package_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience alias for redacting a resource package."""
    return redact_question_package_for_student(package_data)


def redact_diagnostic_bank(bank_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience alias for redacting a diagnostic question bank."""
    return redact_question_package_for_student(bank_data)
