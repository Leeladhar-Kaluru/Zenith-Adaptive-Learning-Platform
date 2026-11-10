"""Doubt sync contracts after the document pipeline was removed.

Doubts are grounded in ZENITH curriculum lesson excerpts when they match,
otherwise answered from general knowledge and labelled as such. Provider
failures are saved as retryable, never as fabricated answers.
"""
import uuid

import pytest

from app.models.doubts import Doubt
from app.models.profiles import UserProfile
from app.services import sync_service as sync_module
from app.services.library_retrieval import CurriculumSnippet
from app.services.sync_service import sync_service


def _no_context(query, **kwargs):
    return "No curriculum reference documents available.", {}


def _one_snippet(query, **kwargs):
    snip = CurriculumSnippet(
        index=1,
        block_id="blk-1",
        source_title="Integers",
        heading="The number line",
        text="Negative numbers lie to the left of zero on the number line.",
    )
    return "[1] Negative numbers lie to the left of zero.", {1: snip}


@pytest.mark.asyncio
async def test_provider_failure_is_retryable_then_answered(db, monkeypatch):
    owner_id = uuid.uuid4()
    calls = {"count": 0}

    async def flaky_chat(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("provider offline")
        return "Negative numbers are to the left of zero."

    monkeypatch.setattr(sync_module, "retrieve_curriculum_context", _no_context)
    monkeypatch.setattr(sync_module.ai_provider, "generate_chat", flaky_chat)

    first = await sync_service.sync_doubt(
        db=db, owner_id=owner_id, client_doubt_id="doubt-1",
        question_text="Where are negative numbers?",
    )
    assert first["status"] == "needs_retry"
    assert first["answerJson"]["retryable"] is True
    assert first["answerJson"]["answer"] is None
    assert db.query(Doubt).filter(Doubt.owner_id == owner_id).count() == 1

    second = await sync_service.sync_doubt(
        db=db, owner_id=owner_id, client_doubt_id="doubt-1",
        question_text="Where are negative numbers?",
    )
    assert second["status"] == "answered"
    assert second["alreadyExisted"] is True
    assert "left of zero" in second["answerJson"]["answer"]
    assert second["answerJson"]["limitations"] == "general_knowledge"
    assert second["answerJson"]["citations"] == []


@pytest.mark.asyncio
async def test_grounded_answer_cites_lesson_excerpts(db, monkeypatch):
    owner_id = uuid.uuid4()
    prompts = []

    async def chat(**kwargs):
        prompts.append(kwargs["messages"][0]["content"])
        return "They sit to the left of zero."

    monkeypatch.setattr(sync_module, "retrieve_curriculum_context", _one_snippet)
    monkeypatch.setattr(sync_module.ai_provider, "generate_chat", chat)

    result = await sync_service.sync_doubt(
        db=db, owner_id=owner_id, client_doubt_id="doubt-2",
        question_text="Where do negative numbers go on the number line?",
    )
    assert result["status"] == "answered"
    assert result["answerJson"]["limitations"] is None
    assert result["answerJson"]["citations"] == [
        {"title": "Integers", "heading": "The number line", "blockId": "blk-1"}
    ]
    assert "Lesson excerpts" in prompts[0]


@pytest.mark.asyncio
async def test_answers_use_the_students_preferred_language(db, monkeypatch):
    owner_id = uuid.uuid4()
    db.add(UserProfile(id=owner_id, role="student", display_name="Learner", preferred_language="te"))
    db.commit()
    prompts = []

    async def chat(**kwargs):
        prompts.append(kwargs["messages"][0]["content"])
        return "Answer."

    monkeypatch.setattr(sync_module, "retrieve_curriculum_context", _no_context)
    monkeypatch.setattr(sync_module.ai_provider, "generate_chat", chat)

    await sync_service.sync_doubt(
        db=db, owner_id=owner_id, client_doubt_id="doubt-3",
        question_text="What is an integer?",
    )
    assert "language code: te" in prompts[0]


@pytest.mark.asyncio
async def test_prompt_never_contains_student_identity(db, monkeypatch):
    owner_id = uuid.uuid4()
    prompts = []

    async def chat(**kwargs):
        prompts.append(kwargs["messages"][0]["content"])
        return "Answer."

    monkeypatch.setattr(sync_module, "retrieve_curriculum_context", _no_context)
    monkeypatch.setattr(sync_module.ai_provider, "generate_chat", chat)

    await sync_service.sync_doubt(
        db=db, owner_id=owner_id, client_doubt_id="doubt-4",
        question_text="What is zero?",
    )
    assert str(owner_id) not in prompts[0]
