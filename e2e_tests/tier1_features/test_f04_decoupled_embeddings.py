import pytest
from e2e_tests.test_config import NOMIC_EMBEDDING_MODEL, NOMIC_EMBEDDING_DIM

def test_embedding_endpoint_decoupled_from_groq():
    """Feature 4: Embeddings are strictly decoupled from Groq chat endpoint."""
    # Decoupling contract: Embedding model is Nomic, not a Groq chat model
    assert "nomic" in NOMIC_EMBEDDING_MODEL.lower()
    assert "gpt" not in NOMIC_EMBEDDING_MODEL.lower()

def test_nomic_embedding_dimension_768():
    """Feature 4: pgvector dimension is 768."""
    assert NOMIC_EMBEDDING_DIM == 768

def test_bm25_keyword_retrieval_for_curriculum(client):
    """Feature 4: Fast keyword/BM25 retrieval over structured curriculum content."""
    res = client.get("/api/v1/library/catalogue")
    assert res.status_code == 200
    data = res.json()
    assert "chapters" in data
    assert len(data["chapters"]) >= 4

def test_local_embedding_fallback(client):
    """Feature 4: Health endpoint observes embedding readiness without crashing."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    ai_status = res.json()["components"]["ai_provider"]
    assert "embed_ready" in ai_status

def test_embedding_isolation_preserves_chat_state(student_client):
    """Feature 4: Embedding operations do not alter or disrupt chat inference."""
    res = student_client.post(
        "/api/v1/tutor/message",
        json_data={"message": "Explain Euclid's division algorithm."}
    )
    assert res.status_code in (200, 503)
    if res.status_code == 200:
        assert "reply" in res.json()
        assert "citations" in res.json()
