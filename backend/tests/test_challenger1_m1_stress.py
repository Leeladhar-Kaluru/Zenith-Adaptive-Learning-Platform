"""
Challenger 1 Empirical Stress Test Suite for Milestone 1 Iteration 2 Rebuild.

Covers:
1. LearningPath ORM model and SQLite/PostgreSQL partial unique index behavior:
   - Table metadata verification for ix_learning_paths_library_slug (unique=True, postgresql_where).
   - PostgreSQL DDL compilation check.
   - SQLite in-memory session verification for multiple library_slug=None records.
   - SQLite partial index verification for multiple is_library=False with identical slugs.
   - SQLite partial index enforcement of IntegrityError on duplicate is_library=True slugs.
2. sync_service.py empirical stress tests:
   - settings imported in sync_service module globals.
   - All 4 tutor branches executed with varied student questions (never raises NameError).
   - Session lifecycle: sync_service never calls db.close(), preserving caller session.
   - Failure handling: simulated LLM failure leaves doubt persisted with status="needs_retry"
     and last_error_code="tutor_unavailable".
"""

import sys
import os
import uuid
import datetime
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine, text, Index
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex
from sqlalchemy.dialects import postgresql, sqlite

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.models.base import Base
from app.models.learning import LearningPath
from app.models.documents import Document, DocumentChunk
from app.models.doubts import Doubt
from app.services.sync_service import sync_service
from app.core.config import settings
from app.core.ai_provider import LLMUnavailableError


def _step_coro(coro):
    """Executes coroutine synchronously without Windows IOCP socketpair deadlocks."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


# =============================================================================
# 1. LearningPath Model and Partial Unique Index Stress Tests
# =============================================================================

def test_learning_path_index_metadata():
    """Verify ix_learning_paths_library_slug exists with unique=True and postgresql_where."""
    table = Base.metadata.tables["learning_paths"]
    slug_indexes = [idx for idx in table.indexes if idx.name == "ix_learning_paths_library_slug"]
    assert len(slug_indexes) == 1, "Index ix_learning_paths_library_slug must exist in table metadata"
    idx = slug_indexes[0]
    assert idx.unique is True, "Index must have unique=True"

    # Verify postgresql_where
    pg_options = idx.dialect_options.get("postgresql", {})
    assert "where" in pg_options, "Index must specify postgresql_where clause"
    pg_where_str = str(pg_options["where"]).strip()
    assert pg_where_str == "is_library IS TRUE", f"Expected 'is_library IS TRUE', got '{pg_where_str}'"


def test_learning_path_ddl_compilation_postgresql():
    """Verify DDL compilation under PostgreSQL dialect preserves the partial WHERE clause."""
    table = Base.metadata.tables["learning_paths"]
    idx = [i for i in table.indexes if i.name == "ix_learning_paths_library_slug"][0]
    ddl = str(CreateIndex(idx).compile(dialect=postgresql.dialect()))
    assert "CREATE UNIQUE INDEX ix_learning_paths_library_slug ON learning_paths (library_slug) WHERE is_library IS TRUE" in ddl


def test_learning_paths_allow_multiple_none_slugs():
    """Verify multiple learning paths can have library_slug=None across library and non-library records."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    paths = [
        LearningPath(owner_id=uuid.uuid4(), grade=10, subject_id="math", outline_json={}, is_library=False, library_slug=None),
        LearningPath(owner_id=uuid.uuid4(), grade=10, subject_id="math", outline_json={}, is_library=False, library_slug=None),
        LearningPath(owner_id=uuid.uuid4(), grade=10, subject_id="science", outline_json={}, is_library=True, library_slug=None),
    ]
    db.add_all(paths)
    db.commit()

    persisted = db.query(LearningPath).filter(LearningPath.library_slug.is_(None)).all()
    assert len(persisted) == 3


def test_learning_paths_partial_unique_index_behavior():
    """
    Empirically verify partial unique index semantics:
    - Multiple records with is_library=False CAN have identical library_slug.
    - Multiple records with is_library=True and identical library_slug MUST fail with IntegrityError.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Recreate index with SQLite partial index syntax (WHERE is_library = 1)
    with engine.connect() as conn:
        conn.execute(text("DROP INDEX IF EXISTS ix_learning_paths_library_slug"))
        conn.execute(text("CREATE UNIQUE INDEX ix_learning_paths_library_slug ON learning_paths (library_slug) WHERE is_library = 1"))
        conn.commit()

    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    # 1. Multiple paths with is_library=False and the exact same slug succeed
    common_slug = "quadratic-equations-foundations"
    p1 = LearningPath(owner_id=uuid.uuid4(), grade=10, subject_id="math", outline_json={}, is_library=False, library_slug=common_slug)
    p2 = LearningPath(owner_id=uuid.uuid4(), grade=10, subject_id="math", outline_json={}, is_library=False, library_slug=common_slug)
    p3 = LearningPath(owner_id=uuid.uuid4(), grade=10, subject_id="math", outline_json={}, is_library=False, library_slug=common_slug)
    db.add_all([p1, p2, p3])
    db.commit()

    non_lib_paths = db.query(LearningPath).filter(LearningPath.library_slug == common_slug, LearningPath.is_library.is_(False)).all()
    assert len(non_lib_paths) == 3

    # 2. First is_library=True with that slug succeeds
    lib_path_1 = LearningPath(owner_id=uuid.uuid4(), grade=10, subject_id="math", outline_json={}, is_library=True, library_slug=common_slug)
    db.add(lib_path_1)
    db.commit()

    # 3. Second is_library=True with that slug MUST fail with IntegrityError
    lib_path_2 = LearningPath(owner_id=uuid.uuid4(), grade=10, subject_id="math", outline_json={}, is_library=True, library_slug=common_slug)
    db.add(lib_path_2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# =============================================================================
# 2. sync_service.py Stress Tests: Settings, 4 Branches, Session & Error Handling
# =============================================================================

def test_sync_service_settings_in_globals():
    """Verify settings is imported in sync_service module globals."""
    from app.services import sync_service as sync_mod
    assert "settings" in sync_mod.__dict__, "'settings' must be present in sync_service module globals"


def test_sync_doubt_all_4_branches_never_raise_name_error():
    """
    Stress-test sync_doubt across all 4 tutor branches with varied student queries:
    Branch 1: No document uploaded (General academic tutoring)
    Branch 2: Document uploaded + summary request (Overview & chapter citations)
    Branch 3: Document uploaded + insufficient evidence (General knowledge fallback)
    Branch 4: Document uploaded + grounded evidence found (Passage citations)
    Verifies that 'settings' resolves in prompt templates without NameError.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    student_id = uuid.uuid4()
    captured_prompts = []

    async def mock_generate_chat(messages, **kwargs):
        prompt = messages[0]["content"]
        captured_prompts.append(prompt)
        app_name = getattr(settings, "APP_NAME", "SETU")
        assert f"You are the {app_name} Academic Tutor" in prompt, "Prompt must include rendered APP_NAME"
        return "Academic response explaining the concept clearly and concisely."

    # --- Branch 1: No document uploaded ---
    with patch("app.services.sync_service.ai_provider.generate_chat", side_effect=mock_generate_chat):
        res1 = _step_coro(sync_service.sync_doubt(
            db=db,
            owner_id=student_id,
            client_doubt_id="branch-1-doubt",
            question_text="What is a rational number?",
        ))
    assert res1["status"] == "answered"
    assert res1["answerJson"]["limitations"] == "general_knowledge"
    assert res1["answerJson"]["citations"] == []

    # Setup document and path for branches 2, 3, 4
    doc = Document(
        id=uuid.uuid4(),
        owner_id=student_id,
        original_filename="class10_math.pdf",
        storage_key="docs/test.pdf",
        mime_type="application/pdf",
        size_bytes=10240,
        status="ready",
    )
    db.add(doc)
    db.commit()

    path = LearningPath(
        owner_id=student_id,
        document_id=doc.id,
        grade=10,
        subject_id="math",
        outline_json={"chapters": [{"title": "Real Numbers", "pageStart": 1, "pageEnd": 12}]},
        is_library=False,
    )
    db.add(path)
    db.commit()

    # --- Branch 2: Document uploaded + summary request ---
    summary_queries = [
        "Can you summarize this book?",
        "Give me an overview of the uploaded document",
        "What is this book about and what is the outline?",
    ]
    for idx, sq in enumerate(summary_queries):
        with patch("app.services.sync_service.ai_provider.generate_chat", side_effect=mock_generate_chat):
            res2 = _step_coro(sync_service.sync_doubt(
                db=db,
                owner_id=student_id,
                client_doubt_id=f"branch-2-summary-{idx}",
                question_text=sq,
            ))
        assert res2["status"] == "answered"
        assert len(res2["answerJson"]["citations"]) >= 1

    # --- Branch 3: Document uploaded + insufficient evidence ---
    async def mock_hybrid_empty(**kwargs):
        return {"results": [], "insufficient_evidence": True}

    with patch("app.services.sync_service.ai_provider.generate_chat", side_effect=mock_generate_chat), \
         patch("app.services.sync_service.retrieval_service.hybrid_search", side_effect=mock_hybrid_empty):
        res3 = _step_coro(sync_service.sync_doubt(
            db=db,
            owner_id=student_id,
            client_doubt_id="branch-3-insufficient",
            question_text="What is the speed of light in vacuum?",
        ))
    assert res3["status"] == "answered"
    assert res3["answerJson"]["limitations"] == "general_knowledge"

    # --- Branch 4: Document uploaded + grounded evidence ---
    async def mock_hybrid_found(**kwargs):
        return {
            "results": [{
                "citationId": "cite_euclid_01",
                "documentVersionId": str(doc.id),
                "pageStart": 4,
                "pageEnd": 5,
                "headingPath": ["Real Numbers", "Euclid Lemma"],
                "text": "For given positive integers a and b, there exist unique integers q and r such that a = bq + r, 0 <= r < b.",
            }],
            "insufficient_evidence": False,
        }

    with patch("app.services.sync_service.ai_provider.generate_chat", side_effect=mock_generate_chat), \
         patch("app.services.sync_service.retrieval_service.hybrid_search", side_effect=mock_hybrid_found):
        res4 = _step_coro(sync_service.sync_doubt(
            db=db,
            owner_id=student_id,
            client_doubt_id="branch-4-grounded",
            question_text="State Euclid's division lemma for integers a and b",
        ))
    assert res4["status"] == "answered"
    assert len(res4["answerJson"]["citations"]) == 1
    assert res4["answerJson"]["citations"][0]["citationId"] == "cite_euclid_01"

    # All branches were executed without any NameError
    assert len(captured_prompts) == 6


def test_sync_doubt_preserves_session_lifecycle():
    """
    Stress-test: sync_service must NEVER call db.close() on the caller's session.
    The session must remain open, healthy, and usable for subsequent queries.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    caller_db = TestingSession()

    close_calls = 0
    orig_close = caller_db.close
    def mock_close():
        nonlocal close_calls
        close_calls += 1
        orig_close()
    caller_db.close = mock_close

    async def mock_generate_chat(*args, **kwargs):
        return "Response from LLM."

    with patch("app.services.sync_service.ai_provider.generate_chat", side_effect=mock_generate_chat):
        # Execute 3 consecutive doubts on the same session
        for i in range(3):
            res = _step_coro(sync_service.sync_doubt(
                db=caller_db,
                owner_id=uuid.uuid4(),
                client_doubt_id=f"session-test-doubt-{i}",
                question_text=f"Question number {i}",
            ))
            assert res["status"] == "answered"

    assert close_calls == 0, "CRITICAL: sync_service called caller_db.close()!"
    assert caller_db.is_active, "Caller DB session must remain active"

    # Verify session can execute new queries without error
    all_doubts = caller_db.query(Doubt).all()
    assert len(all_doubts) == 3


def test_sync_doubt_failure_handling_persists_needs_retry():
    """
    Stress-test: when external LLM raises an exception during sync_doubt,
    the doubt row MUST be persisted in DB with status='needs_retry'
    and last_error_code='tutor_unavailable'.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    student_id = uuid.uuid4()
    doubt_client_id = f"fail-retry-{uuid.uuid4()}"
    q_text = "How do you calculate compound interest?"

    # Simulate Groq 503 / timeout / LLM error
    async def failing_llm(*args, **kwargs):
        raise LLMUnavailableError("Groq endpoint timeout: 503 Service Unavailable")

    with patch("app.services.sync_service.ai_provider.generate_chat", side_effect=failing_llm):
        res = _step_coro(sync_service.sync_doubt(
            db=db,
            owner_id=student_id,
            client_doubt_id=doubt_client_id,
            question_text=q_text,
        ))

    assert res["status"] == "needs_retry"
    assert res["answerJson"]["limitations"] == "tutor_unavailable"
    assert res["answerJson"]["retryable"] is True

    # Check database persistence
    saved = db.query(Doubt).filter(Doubt.client_doubt_id == doubt_client_id).first()
    assert saved is not None, "Doubt must be persisted in database despite LLM failure"
    assert saved.status == "needs_retry"
    assert saved.last_error_code == "tutor_unavailable"
    assert saved.answered_at is None
    assert saved.question_text == q_text
