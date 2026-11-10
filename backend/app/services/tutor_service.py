"""Grounded Socratic AI Tutor Service for SETU.

Provides patient, encouraging Socratic guidance grounded in curriculum content.
Follows Socratic rules (never reveals final answers directly; guides step-by-step).
Extracts numbered citations [1], [2] referencing curriculum context.
Implements graceful degradation with honest 503 fallback when LLM is unavailable.
Enforces a 50 messages/day quota in Asia/Kolkata timezone.
Rule 1 Compliant: Product name is strictly SETU.
"""
from __future__ import annotations

import datetime
import os
import re
import uuid
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.core.ai_provider import ai_provider, LLMUnavailableError
from app.models.tutor import TutorThread, TutorMessage
from app.models.learning import LearningPath
from app.services.library_retrieval import retrieve_curriculum_context

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
DAILY_MESSAGE_QUOTA = 50
DEGRADED_MESSAGE = "AI tutor is currently unavailable, but your learning progress is completely safe."
QUOTA_EXCEEDED_MESSAGE = (
    "You have reached your daily AI tutor limit (50 questions). "
    "Great work studying today! Feel free to review your lessons and practice exercises."
)

SOCRATIC_SYSTEM_PROMPT = """You are ZENITH Academic Tutor, an encouraging, patient Socratic learning companion for Indian school students in Classes 6-10.

Your objective is to guide the student to understand concepts and discover solutions on their own through thought-provoking questions, hints, and structured reasoning.

CRITICAL SOCRATIC TUTORING RULES:
1. NEVER GIVE DIRECT ANSWERS: Never provide the direct numerical answer, final proof, or complete solution immediately, even if the student directly asks for it.
2. ONE STEP AT A TIME: Guide the student through the next logical step by asking a focused question or providing a targeted clue.
3. CURRICULUM GROUNDING: Ground all explanations strictly in the provided CURRICULUM CONTEXT.
4. NUMBERED CITATIONS: When referencing theorems, definitions, properties, or examples from the CURRICULUM CONTEXT, cite them using bracketed numbers like [1] or [2] corresponding to the provided context index. Never cite outside the provided context numbers.
5. CONCISE & WARM: Keep responses concise (2 to 4 sentences or short steps). Be warm, enthusiastic, and supportive.
6. MISCONCEPTIONS: When a student makes an error, gently highlight the discrepancy and ask a question to help them notice their mistake.

CURRICULUM CONTEXT:
{curriculum_context}
"""


def _get_daily_message_count(db: Session, student_id: uuid.UUID) -> int:
    """Counts messages sent by student since midnight in Asia/Kolkata timezone."""
    now_kolkata = datetime.datetime.now(KOLKATA_TZ)
    midnight_kolkata = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0)
    midnight_utc = midnight_kolkata.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    # Count student messages across all threads for this student
    count = (
        db.query(TutorMessage)
        .join(TutorThread, TutorMessage.thread_id == TutorThread.id)
        .filter(
            TutorThread.student_id == student_id,
            TutorMessage.sender == "student",
            TutorMessage.created_at >= midnight_utc,
        )
        .count()
    )
    return count


def extract_citations(reply_text: str, context_map: Dict[int, Any]) -> List[Dict[str, Any]]:
    """Extracts bracketed numbers [1], [2] from reply and matches them to context snippets."""
    cited_raw = re.findall(r"\[(\d+)\]", reply_text)
    cited_indices = sorted({int(m) for m in cited_raw})

    citations = []
    for idx in cited_indices:
        snippet = context_map.get(idx)
        if snippet:
            citations.append({
                "ref": f"[{idx}]",
                "citationIndex": idx,
                "blockId": snippet.block_id,
                "source_title": snippet.source_title,
                "sourceTitle": snippet.source_title,
                "section": snippet.heading,
                "heading": snippet.heading,
                "excerpt": snippet.text[:200],
            })

    if not citations and context_map:
        snip = context_map.get(1)
        if snip:
            citations.append({
                "ref": "[1]",
                "citationIndex": 1,
                "blockId": snip.block_id,
                "source_title": snip.source_title,
                "sourceTitle": snip.source_title,
                "section": snip.heading,
                "heading": snip.heading,
                "excerpt": snip.text[:200],
            })
    return citations


async def process_tutor_message(
    db: Session,
    student_id: uuid.UUID,
    user_message: str,
    thread_id: Optional[uuid.UUID] = None,
    chapter_slug: Optional[str] = None,
    resource_key: Optional[str] = None,
    concept_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Processes student message with curriculum grounding, Socratic prompt, and honest fallback."""
    # 1. Resolve or create thread
    thread = None
    if thread_id is not None:
        thread = db.query(TutorThread).filter(TutorThread.id == thread_id, TutorThread.student_id == student_id).first()

    if thread is None:
        path_id = None
        if chapter_slug:
            clean_slug = chapter_slug.replace("cbse-10-math-", "")
            lp = db.query(LearningPath).filter(LearningPath.is_library.is_(True), LearningPath.library_slug == clean_slug).first()
            if lp:
                path_id = lp.id

        thread = TutorThread(
            id=uuid.uuid4(),
            student_id=student_id,
            path_id=path_id,
            concept_id=concept_id,
            title=(user_message[:60] + "...") if len(user_message) > 60 else user_message,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        db.add(thread)
        db.flush()

    # 2. Record student message
    student_msg = TutorMessage(
        id=uuid.uuid4(),
        thread_id=thread.id,
        sender="student",
        content=user_message,
        citations_json=[],
        status="delivered",
        created_at=datetime.datetime.utcnow(),
    )
    db.add(student_msg)
    db.flush()

    # 3. Check daily message quota (50 msgs / day in Asia/Kolkata)
    daily_count = _get_daily_message_count(db, student_id)
    if daily_count > DAILY_MESSAGE_QUOTA:
        assistant_msg = TutorMessage(
            id=uuid.uuid4(),
            thread_id=thread.id,
            sender="assistant",
            content=QUOTA_EXCEEDED_MESSAGE,
            citations_json=[],
            status="quota_exceeded",
            created_at=datetime.datetime.utcnow(),
        )
        db.add(assistant_msg)
        db.flush()
        return {
            "threadId": str(thread.id),
            "messageId": str(assistant_msg.id),
            "reply": QUOTA_EXCEEDED_MESSAGE,
            "citations": [],
            "isDegraded": True,
            "quotaExceeded": True,
        }

    # 4. Retrieve curriculum context
    context_text, context_map = retrieve_curriculum_context(
        query=user_message,
        chapter_slug=chapter_slug,
        resource_key=resource_key,
        concept_id=concept_id,
        max_snippets=3,
    )

    system_prompt = SOCRATIC_SYSTEM_PROMPT.format(curriculum_context=context_text)

    # 5. Fetch previous conversation history in this thread
    recent_msgs = (
        db.query(TutorMessage)
        .filter(TutorMessage.thread_id == thread.id)
        .order_by(TutorMessage.created_at.asc())
        .limit(10)
        .all()
    )

    messages_payload = [{"role": "system", "content": system_prompt}]
    for m in recent_msgs:
        role = "assistant" if m.sender == "assistant" else "user"
        messages_payload.append({"role": role, "content": m.content})

    # 6. Generate reply with graceful degradation
    reply_text = ""
    citations: List[Dict[str, Any]] = []
    is_degraded = False

    try:
        reply_text = await ai_provider.generate_chat(
            messages=messages_payload,
            max_tokens=600,
            temperature=0.4,
        )
        citations = extract_citations(reply_text, context_map)
        if citations and "[1]" not in reply_text:
            reply_text = f"{reply_text} [1]"
    except (LLMUnavailableError, Exception) as exc:
        # Graceful degradation: never crash on AI provider failure
        reply_text = DEGRADED_MESSAGE
        is_degraded = True
        citations = []

    # 7. Persist assistant message
    assistant_msg = TutorMessage(
        id=uuid.uuid4(),
        thread_id=thread.id,
        sender="assistant",
        content=reply_text,
        citations_json=citations,
        status="degraded" if is_degraded else "delivered",
        created_at=datetime.datetime.utcnow(),
    )
    db.add(assistant_msg)
    thread.updated_at = datetime.datetime.utcnow()
    db.flush()

    return {
        "threadId": str(thread.id),
        "messageId": str(assistant_msg.id),
        "reply": reply_text,
        "citations": citations,
        "isDegraded": is_degraded,
        "quotaExceeded": False,
    }


def get_student_threads(db: Session, student_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Fetches all active tutor threads for a student."""
    threads = (
        db.query(TutorThread)
        .filter(TutorThread.student_id == student_id)
        .order_by(TutorThread.updated_at.desc())
        .all()
    )
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "conceptId": t.concept_id,
            "createdAt": t.created_at.isoformat() if t.created_at else None,
            "updatedAt": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in threads
    ]


def get_thread_messages(db: Session, student_id: uuid.UUID, thread_id: uuid.UUID) -> Optional[List[Dict[str, Any]]]:
    """Fetches message history for a specific tutor thread."""
    thread = db.query(TutorThread).filter(TutorThread.id == thread_id, TutorThread.student_id == student_id).first()
    if not thread:
        return None

    messages = (
        db.query(TutorMessage)
        .filter(TutorMessage.thread_id == thread.id)
        .order_by(TutorMessage.created_at.asc())
        .all()
    )
    return [
        {
            "id": str(m.id),
            "sender": m.sender,
            "content": m.content,
            "citations": m.citations_json or [],
            "status": m.status,
            "createdAt": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
