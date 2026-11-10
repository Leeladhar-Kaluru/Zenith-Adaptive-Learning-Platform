import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.doubts import Doubt
from app.models.profiles import UserProfile
from app.services.library_retrieval import retrieve_curriculum_context
from app.services.text_sanitize import sanitize_prose
from app.core.ai_provider import ai_provider
from app.core.config import settings

logger = logging.getLogger(__name__)

def _student_language(db: Session, owner_id: uuid.UUID) -> str:
    profile = (
        db.query(UserProfile.preferred_language)
        .filter(UserProfile.id == owner_id)
        .first()
    )
    language = (profile[0] if profile else None) or "en"
    return language.strip()[:20]


class SyncService:
    async def sync_doubt(
        self,
        db: Session,
        owner_id: uuid.UUID,
        client_doubt_id: str,
        question_text: str,
        path_id: Optional[uuid.UUID] = None,
        lesson_version_id: Optional[uuid.UUID] = None,
        block_id: Optional[str] = None,
        source_page: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Idempotent doubt intake. An answered doubt is returned as-is. A doubt
        that previously failed is retried instead of replayed forever.
        """
        existing = db.query(Doubt).filter(
            Doubt.owner_id == owner_id,
            Doubt.client_doubt_id == client_doubt_id
        ).first()

        if existing and existing.status == "answered":
            return {
                "id": str(existing.id),
                "clientDoubtId": existing.client_doubt_id,
                "status": existing.status,
                "questionText": existing.question_text,
                "answerJson": existing.answer_json,
                "alreadyExisted": True
            }

        already_existed = existing is not None
        if existing:
            doubt = existing
            doubt.status = "processing"
            doubt.last_error_code = None
        else:
            doubt = Doubt(
                owner_id=owner_id,
                client_doubt_id=client_doubt_id,
                path_id=path_id,
                lesson_version_id=lesson_version_id,
                block_id=block_id,
                source_page=source_page,
                question_text=question_text,
                status="processing",
                submitted_at=datetime.datetime.utcnow(),
            )
            db.add(doubt)
        db.flush()
        doubt_id = doubt.id
        db.commit()

        try:
            reply_language = _student_language(db, owner_id)
            context_text, snippets = retrieve_curriculum_context(question_text, max_snippets=3)
            grounded = bool(snippets)
            app_name = getattr(settings, "APP_NAME", "ZENITH")
            if grounded:
                guidance = (
                    "Use the numbered ZENITH lesson excerpts below as your primary source. "
                    "If they do not cover the question, say so briefly and explain from general knowledge.\n"
                    f"Lesson excerpts:\n{context_text}\n"
                )
            else:
                guidance = "Explain accurately from general knowledge suitable for a Class 6-10 student.\n"
            prompt = (
                f"You are the {app_name} tutor for a school student in Classes 6-10.\n"
                "Answer in at most 140 words, in plain language, without a greeting.\n"
                "Never write LaTeX or raw formatting; write numbers and units in plain text.\n"
                f"{guidance}"
                f"Reply in the student's preferred language (language code: {reply_language}).\n"
                f"Student question: {question_text}\n"
            )
            llm_answer = await ai_provider.generate_chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1200,
                require_complete=True,
            )
            if not llm_answer or not str(llm_answer).strip():
                raise RuntimeError("empty tutor response")
            citations = [
                {"title": snip.source_title, "heading": snip.heading, "blockId": snip.block_id}
                for snip in snippets.values()
            ] if grounded else []
            answer_payload = {
                "answer": sanitize_prose(llm_answer),
                "citations": citations,
                "limitations": None if grounded else "general_knowledge",
                "answeredAt": datetime.datetime.utcnow().isoformat(),
            }

            doubt.status = "answered"
            doubt.last_error_code = None
            doubt.answer_json = answer_payload
            doubt.answered_at = datetime.datetime.utcnow()
            db.commit()
            db.refresh(doubt)
        except Exception as e:
            logger.exception(f"Error resolving doubt {client_doubt_id}: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            try:
                doubt_rec = db.query(Doubt).filter(Doubt.id == doubt_id).first()
                if doubt_rec:
                    doubt_rec.status = "needs_retry"
                    doubt_rec.last_error_code = "tutor_unavailable"
                    doubt_rec.answer_json = {
                        "answer": None,
                        "citations": [],
                        "limitations": "tutor_unavailable",
                        "retryable": True,
                        "message": "The tutor is temporarily unavailable. Your question is saved; retry in a moment."
                    }
                    doubt_rec.answered_at = None
                    db.commit()
                    db.refresh(doubt_rec)
                    doubt = doubt_rec
            except Exception as save_err:
                logger.warning(f"Could not persist fallback doubt state: {save_err}")

        return {
            "id": str(doubt.id),
            "clientDoubtId": doubt.client_doubt_id,
            "status": doubt.status,
            "questionText": doubt.question_text,
            "answerJson": doubt.answer_json,
            "alreadyExisted": already_existed
        }


sync_service = SyncService()
