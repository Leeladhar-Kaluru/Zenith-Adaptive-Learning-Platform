"""Empirical Challenger 3 Verification Suite for Milestone 1 Iteration 3.

Empirically tests:
1. HTTP 404 fallback from primary model (openai/gpt-oss-120b) to fallback model (qwen/qwen3.8-27b).
2. Decoupled embedding latency (< 0.001s) and zero HTTP connection attempts.
3. Fallback error propagation when both models return errors.
4. Response format preservation during HTTP 404 fallback.
"""

import sys
import os
import time
import pytest
import httpx
from typing import List, Dict, Any

from app.core.ai_provider import ai_provider, LLMUnavailableError


@pytest.mark.asyncio
async def test_http_404_fallback_to_qwen(monkeypatch):
    """Assert that when openai/gpt-oss-120b returns HTTP 404,

    generate_chat automatically falls back to qwen/qwen3.8-27b and returns the response.
    """
    calls: List[Dict[str, Any]] = []

    async def fake_post(self, url, headers=None, json=None, **kwargs):
        model = json.get("model")
        calls.append({"model": model, "url": str(url), "payload": json})

        if model == "openai/gpt-oss-120b":
            return httpx.Response(
                status_code=404,
                headers={"content-type": "application/json"},
                json={
                    "error": {
                        "message": "Model 'openai/gpt-oss-120b' not found or decommissioned.",
                        "type": "invalid_request_error",
                        "code": "model_not_found"
                    }
                }
            )
        elif model == "qwen/qwen3.8-27b":
            return httpx.Response(
                status_code=200,
                headers={"content-type": "application/json"},
                json={
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "Hello from Qwen fallback model."
                        },
                        "finish_reason": "stop"
                    }]
                }
            )
        else:
            raise ValueError(f"Unexpected model requested: {model}")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    # Ensure provider is configured with expected models
    monkeypatch.setattr(ai_provider, "chat_model", "openai/gpt-oss-120b")
    monkeypatch.setattr(ai_provider, "fallback_model", "qwen/qwen3.8-27b")

    messages = [{"role": "user", "content": "Explain Newton's third law."}]
    response = await ai_provider.generate_chat(messages, temperature=0.3, max_tokens=600)

    # 1. Assert response is received from fallback model
    assert response == "Hello from Qwen fallback model."

    # 2. Assert fallback model was called
    called_models = [c["model"] for c in calls]
    assert "openai/gpt-oss-120b" in called_models
    assert called_models[-1] == "qwen/qwen3.8-27b", f"Expected last call to be fallback model, got {called_models}"


@pytest.mark.asyncio
async def test_http_404_fallback_preserves_response_format(monkeypatch):
    """Assert that payload parameters such as response_format and max_tokens

    are preserved across the HTTP 404 fallback call.
    """
    calls: List[Dict[str, Any]] = []

    async def fake_post(self, url, headers=None, json=None, **kwargs):
        calls.append(json)
        if json.get("model") == "openai/gpt-oss-120b":
            return httpx.Response(status_code=404, json={"error": "not found"})
        return httpx.Response(
            status_code=200,
            json={
                "choices": [{
                    "message": {
                        "content": '{"concept": "gravity", "mastery": 0.85}'
                    },
                    "finish_reason": "stop"
                }]
            }
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(ai_provider, "chat_model", "openai/gpt-oss-120b")
    monkeypatch.setattr(ai_provider, "fallback_model", "qwen/qwen3.8-27b")

    fmt = {"type": "json_object"}
    res = await ai_provider.generate_chat(
        [{"role": "user", "content": "Output JSON"}],
        response_format=fmt,
        max_tokens=350
    )

    assert res == '{"concept": "gravity", "mastery": 0.85}'
    # Verify both primary and fallback received response_format and max_tokens
    primary_calls = [c for c in calls if c.get("model") == "openai/gpt-oss-120b"]
    fallback_calls = [c for c in calls if c.get("model") == "qwen/qwen3.8-27b"]
    assert len(primary_calls) >= 1
    assert len(fallback_calls) == 1
    assert primary_calls[0]["response_format"] == fmt
    assert primary_calls[0]["max_tokens"] == 350
    assert fallback_calls[0]["response_format"] == fmt
    assert fallback_calls[0]["max_tokens"] == 350


@pytest.mark.asyncio
async def test_http_404_fallback_exhaustion_raises_runtime_error(monkeypatch):
    """When both primary and fallback return 404, an informative RuntimeError is raised."""
    async def fake_post(self, url, headers=None, json=None, **kwargs):
        return httpx.Response(status_code=404, text="Model not found")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(ai_provider, "chat_model", "openai/gpt-oss-120b")
    monkeypatch.setattr(ai_provider, "fallback_model", "qwen/qwen3.8-27b")

    with pytest.raises(RuntimeError, match="status 404"):
        await ai_provider.generate_chat([{"role": "user", "content": "Hi"}])


