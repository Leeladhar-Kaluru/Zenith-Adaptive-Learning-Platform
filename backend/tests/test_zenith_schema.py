import pytest
import uuid
from datetime import date
from sqlalchemy import inspect
from app.models.base import Base
from app.models.learning import LearningPath
from app.models.library import (
    Concept,
    ConceptEdge,
    ConceptChapter,
    LibraryEnrollment,
    ResourceProgress,
    ContentRequest,
    LibraryPublicationEvent,
)
from app.models.mastery import BktState, BktEvent
from app.models.rewards import StudentReward, RewardEvent, Badge, StudentBadge
from app.models.diagnostics import DiagnosticSession, DiagnosticItem
from app.models.tutor import TutorThread, TutorMessage
from app.core.config import settings
from app.core.ai_provider import AIProviderService, EmbeddingUnavailableError, LLMUnavailableError


def _step_coro(coro):
    """Executes a coroutine synchronously without Windows IOCP socketpair deadlocks."""
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


def test_migration_009_tables_registered_in_metadata():
    """Verify all 17 new Zenith tables exist in SQLAlchemy Base metadata."""
    expected_tables = {
        "concepts",
        "concept_edges",
        "concept_chapters",
        "library_enrollments",
        "resource_progress",
        "bkt_states",
        "bkt_events",
        "student_rewards",
        "reward_events",
        "badges",
        "student_badges",
        "diagnostic_sessions",
        "diagnostic_items",
        "tutor_threads",
        "tutor_messages",
        "content_requests",
        "library_publication_events",
    }
    registered_tables = set(Base.metadata.tables.keys())
    for table_name in expected_tables:
        assert table_name in registered_tables, f"Table '{table_name}' missing from Base.metadata"


def test_learning_paths_altered_columns():
    """Verify altered columns on learning_paths exist with correct types."""
    table = Base.metadata.tables["learning_paths"]
    columns = table.columns

    assert "is_library" in columns, "learning_paths missing is_library"
    assert "library_slug" in columns, "learning_paths missing library_slug"
    assert "library_status" in columns, "learning_paths missing library_status"
    assert "board_id" in columns, "learning_paths missing board_id"


def test_concept_model_defaults_and_fields():
    """Verify Concept model attributes and default BKT parameters."""
    c = Concept(
        id="cbse-10-math-real-numbers-euclid",
        slug="real-numbers-euclid",
        title="Euclid's Division Lemma",
        grade=10,
        subject_id="subject-math",
    )
    assert c.id == "cbse-10-math-real-numbers-euclid"
    assert c.slug == "real-numbers-euclid"
    assert c.grade == 10
    assert c.p_l0 == 0.25
    assert c.p_t == 0.15
    assert c.p_g == 0.20
    assert c.p_s == 0.10


def test_concept_edge_unique_constraint():
    """Verify concept_edges table has composite unique constraint on (from_concept_id, to_concept_id)."""
    table = Base.metadata.tables["concept_edges"]
    uq_names = [uq.name for uq in table.constraints if hasattr(uq, "columns")]
    assert "uq_concept_edge_from_to" in uq_names


def test_bkt_state_model():
    """Verify BktState model defaults and unique constraint."""
    st_id = uuid.uuid4()
    bkt = BktState(
        student_id=st_id,
        concept_id="cbse-10-math-real-numbers-euclid",
    )
    assert bkt.p_know == 0.25
    assert bkt.streak == 0
    assert bkt.mastery_band == "not_enough_evidence"
    assert bkt.is_gap is False
    assert bkt.gap_signal_count == 0

    table = Base.metadata.tables["bkt_states"]
    uq_names = [uq.name for uq in table.constraints if hasattr(uq, "columns")]
    assert "uq_bkt_state_student_concept" in uq_names


def test_student_reward_model():
    """Verify StudentReward attributes and daily streak tracking."""
    st_id = uuid.uuid4()
    reward = StudentReward(
        student_id=st_id,
        total_xp=150,
        zenith_coins=30,
        current_streak_days=3,
        last_active_date=date(2026, 11, 6),
    )
    assert reward.total_xp == 150
    assert reward.zenith_coins == 30
    assert reward.current_level == 1
    assert reward.current_streak_days == 3
    assert reward.last_active_date == date(2026, 11, 6)


def test_diagnostic_session_and_items():
    """Verify DiagnosticSession and DiagnosticItem relationship structure."""
    sess_id = uuid.uuid4()
    st_id = uuid.uuid4()
    path_id = uuid.uuid4()

    session = DiagnosticSession(
        id=sess_id,
        student_id=st_id,
        path_id=path_id,
        status="in_progress",
        total_items=8,
    )
    assert session.total_items == 8
    assert session.status == "in_progress"

    item = DiagnosticItem(
        session_id=sess_id,
        item_index=1,
        concept_id="cbse-10-math-real-numbers-euclid",
        is_prerequisite_probe=False,
        question_json={"prompt": "State Euclid's lemma"},
    )
    assert item.item_index == 1
    assert item.is_prerequisite_probe is False


def test_tutor_thread_and_messages():
    """Verify TutorThread and TutorMessage schemas."""
    st_id = uuid.uuid4()
    thread = TutorThread(
        student_id=st_id,
        title="Help with Polynomial roots",
    )
    assert thread.student_id == st_id

    msg = TutorMessage(
        thread_id=thread.id,
        sender="student",
        content="What is a quadratic polynomial?",
    )
    assert msg.sender == "student"
    assert msg.status == "delivered"


def test_ai_provider_groq_auth_and_decoupling(monkeypatch):
    """Verify AIProviderService injects Bearer auth for Groq and decouples embeddings."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test_groq_key_secret_123")
    monkeypatch.setattr(settings, "EMBEDDING_BASE_URL", None)

    provider = AIProviderService()
    assert provider.provider == "groq"
    assert provider.chat_base_url == "https://api.groq.com/openai/v1"
    assert provider.chat_model == "openai/gpt-oss-120b"
    assert provider.fallback_model == "qwen/qwen3.8-27b"
    assert provider.embed_base_url is None

    headers = provider._auth_headers()
    assert headers["Authorization"] == "Bearer test_groq_key_secret_123"
    assert headers["Content-Type"] == "application/json"


def test_ai_provider_groq_rejects_embedding_without_embed_url(monkeypatch):
    """Verify Groq provider refuses to send embedding requests to Groq endpoint."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(settings, "EMBEDDING_BASE_URL", None)

    provider = AIProviderService()
    coro = provider.get_embeddings_batch(["Sample text chunk"])
    with pytest.raises(EmbeddingUnavailableError, match="not supported on Groq"):
        _step_coro(coro)


def test_ai_provider_lmstudio_preservation(monkeypatch):
    """Verify local LM Studio configuration remains intact."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setattr(settings, "LLM_MODEL", "google/gemma-4-e4b")
    monkeypatch.setattr(settings, "EMBEDDING_BASE_URL", None)

    provider = AIProviderService()
    assert provider.provider == "lmstudio"
    assert provider.chat_base_url == "http://127.0.0.1:1234/v1"
    assert provider.chat_model == "google/gemma-4-e4b"
    assert provider.embed_base_url == "http://127.0.0.1:1234/v1"


def test_ai_provider_fallback_on_429(monkeypatch):
    """Verify 429 rate limit triggers backoff and fallback model attempt."""
    import httpx
    import asyncio

    call_records = []

    class FakeResponse:
        def __init__(self, status_code, data, headers=None):
            self.status_code = status_code
            self._data = data
            self.headers = headers or {}
            self.text = str(data)

        def json(self):
            return self._data

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, headers=None, json=None):
            model = json.get("model") if json else "unknown"
            call_records.append(model)
            # Primary model returns 429
            if model == "openai/gpt-oss-120b":
                return FakeResponse(429, {"error": "Rate limit exceeded"}, {"retry-after": "0.0"})
            # Fallback model succeeds
            if model == "qwen/qwen3.8-27b":
                return FakeResponse(200, {
                    "choices": [{
                        "message": {"content": "This is an answer from the fallback model."},
                        "finish_reason": "stop"
                    }]
                })
            return FakeResponse(500, {"error": "Unknown model"})

    async def noop_sleep(*args):
        pass

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    monkeypatch.setattr(asyncio, "sleep", noop_sleep)

    provider = AIProviderService()
    coro = provider.generate_chat([{"role": "user", "content": "Explain fractions"}])
    answer = _step_coro(coro)
    assert answer == "This is an answer from the fallback model."
    assert "openai/gpt-oss-120b" in call_records
    assert "qwen/qwen3.8-27b" in call_records
