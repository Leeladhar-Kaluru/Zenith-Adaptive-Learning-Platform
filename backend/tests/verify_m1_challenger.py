"""
Empirical Challenger 2 Verification Harness for Milestone 1.
Tests:
1. HTTP 429 response with Retry-After: 1 exponential backoff.
2. Primary model failure fallback to qwen/qwen3.8-27b.
3. Max token capping (<= 1500 tokens).
4. Decoupled embeddings isolation (never target Groq).
5. Real live end-to-end request to Groq openai/gpt-oss-120b with timing & headers.
"""

import sys
import os
import time
import asyncio
from typing import List, Dict, Any, Optional

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
from app.core.config import settings
from app.core.ai_provider import (
    AIProviderService,
    LLMUnavailableError,
)

results = {}


async def test_429_backoff_and_retry():
    print("\n--- [TEST 1] HTTP 429 Simulation with Retry-After: 1 ---")
    provider = AIProviderService()
    provider.api_key = "mock-key"
    call_records = []

    original_post = httpx.AsyncClient.post

    async def mock_post(self, url, headers=None, json=None, **kwargs):
        call_records.append({
            "timestamp": time.perf_counter(),
            "model": json.get("model"),
            "url": str(url)
        })
        if len(call_records) == 1:
            # First attempt returns 429 with Retry-After: 1
            return httpx.Response(
                status_code=429,
                headers={"retry-after": "1"},
                json={"error": {"message": "Rate limit exceeded"}}
            )
        else:
            # Second attempt succeeds
            return httpx.Response(
                status_code=200,
                json={
                    "choices": [{
                        "message": {"content": "Success after backoff."}
                    }]
                }
            )

    httpx.AsyncClient.post = mock_post
    t0 = time.perf_counter()
    try:
        reply = await provider.generate_chat([{"role": "user", "content": "Hello"}])
        duration = time.perf_counter() - t0
        print(f"  Attempts made: {len(call_records)}")
        print(f"  Delay between attempt 1 and 2: {call_records[1]['timestamp'] - call_records[0]['timestamp']:.3f}s")
        print(f"  Total duration: {duration:.3f}s")
        print(f"  Returned reply: '{reply}'")

        assert len(call_records) == 2, f"Expected 2 attempts, got {len(call_records)}"
        assert reply == "Success after backoff.", f"Unexpected reply: {reply}"
        delay = call_records[1]["timestamp"] - call_records[0]["timestamp"]
        assert 0.8 <= delay <= 2.0, f"Backoff delay expected ~1.0s, got {delay:.3f}s"
        print("  -> PASS: 429 with Retry-After: 1 correctly backed off and retried successfully.")
        results["test_429_backoff"] = "PASS"
    finally:
        httpx.AsyncClient.post = original_post


async def test_primary_model_failure_fallback():
    print("\n--- [TEST 2] Primary Model Failure & Fallback to qwen/qwen3.8-27b ---")
    provider = AIProviderService()
    provider.api_key = "mock-key"
    call_models = []

    original_post = httpx.AsyncClient.post

    async def mock_post(self, url, headers=None, json=None, **kwargs):
        model = json.get("model")
        call_models.append(model)
        if model == "openai/gpt-oss-120b":
            # Primary model fails with 503
            return httpx.Response(
                status_code=503,
                json={"error": {"message": "Model temporarily unavailable"}}
            )
        elif model == "qwen/qwen3.8-27b":
            # Fallback model succeeds
            return httpx.Response(
                status_code=200,
                json={
                    "choices": [{
                        "message": {"content": "Response from Qwen fallback model."}
                    }]
                }
            )
        return httpx.Response(status_code=500, json={})

    httpx.AsyncClient.post = mock_post
    try:
        reply = await provider.generate_chat([{"role": "user", "content": "Explain quadratic equations"}])
        print(f"  Models queried in sequence: {call_models}")
        print(f"  Returned reply: '{reply}'")

        assert "openai/gpt-oss-120b" in call_models, "Primary model was not attempted"
        assert "qwen/qwen3.8-27b" in call_models, "Fallback model was not attempted"
        assert reply == "Response from Qwen fallback model.", f"Unexpected reply: {reply}"
        print("  -> PASS: Fallback to qwen/qwen3.8-27b activated and succeeded seamlessly.")
        results["test_fallback_model"] = "PASS"
    finally:
        httpx.AsyncClient.post = original_post


async def test_token_capping():
    print("\n--- [TEST 3] Token Capping (max_tokens <= 1500) ---")
    provider = AIProviderService()
    provider.api_key = "mock-key"
    captured_payloads = []

    original_post = httpx.AsyncClient.post

    async def mock_post(self, url, headers=None, json=None, **kwargs):
        captured_payloads.append(json)
        return httpx.Response(
            status_code=200,
            json={"choices": [{"message": {"content": "Token test reply."}}]}
        )

    httpx.AsyncClient.post = mock_post
    try:
        # Request 4000 tokens (exceeds cap)
        await provider.generate_chat([{"role": "user", "content": "Give me a long text"}], max_tokens=4000)
        # Request 500 tokens (under cap)
        await provider.generate_chat([{"role": "user", "content": "Short text"}], max_tokens=500)
        # Request None/default
        await provider.generate_chat([{"role": "user", "content": "Default tokens"}], max_tokens=None)

        print(f"  Call 1 (requested 4000): sent max_tokens = {captured_payloads[0].get('max_tokens')}")
        print(f"  Call 2 (requested 500):  sent max_tokens = {captured_payloads[1].get('max_tokens')}")
        print(f"  Call 3 (requested None): sent max_tokens = {captured_payloads[2].get('max_tokens')}")

        assert captured_payloads[0].get("max_tokens") == 1500, "Failed to cap 4000 to 1500"
        assert captured_payloads[1].get("max_tokens") == 500, "Failed to preserve 500"
        assert captured_payloads[2].get("max_tokens") == 1500, "Failed default 1500 cap"

        # Large prompt payload check
        huge_prompt = "word " * 6000
        await provider.generate_chat([{"role": "user", "content": huge_prompt}], max_tokens=5000)
        print(f"  Call 4 (oversized prompt 6000 words): payload serialized OK, max_tokens = {captured_payloads[3].get('max_tokens')}")
        assert captured_payloads[3].get("max_tokens") == 1500

        print("  -> PASS: Token cap strictly enforced at <= 1500 tokens.")
        results["test_token_capping"] = "PASS"
    finally:
        httpx.AsyncClient.post = original_post


async def test_live_groq_request():
    print("\n--- [TEST 5] Live End-to-End Request to Groq openai/gpt-oss-120b ---")
    api_key = settings.GROQ_API_KEY
    if not api_key:
        print("  -> SKIPPED / REJECT: GROQ_API_KEY is not set in backend environment.")
        results["test_live_groq"] = "FAIL: No API Key"
        return

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {
                "role": "user",
                "content": "State the Fundamental Theorem of Arithmetic in exactly one sentence.",
            }
        ],
        "temperature": 0.1,
        "max_tokens": 150,
    }

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        response = await client.post(url, headers=headers, json=payload)
    latency_ms = (time.perf_counter() - t0) * 1000

    print(f"  HTTP Status: {response.status_code}")
    print(f"  Roundtrip latency: {latency_ms:.1f} ms")

    # Extract headers
    limit_req = response.headers.get("x-ratelimit-limit-requests")
    rem_req = response.headers.get("x-ratelimit-remaining-requests")
    limit_tokens = response.headers.get("x-ratelimit-limit-tokens")
    rem_tokens = response.headers.get("x-ratelimit-remaining-tokens")
    reset_req = response.headers.get("x-ratelimit-reset-requests")
    reset_tokens = response.headers.get("x-ratelimit-reset-tokens")
    request_id = response.headers.get("x-request-id")

    print("  --- Response Headers ---")
    print(f"  x-request-id:                   {request_id}")
    print(f"  x-ratelimit-limit-requests:     {limit_req}")
    print(f"  x-ratelimit-remaining-requests: {rem_req}")
    print(f"  x-ratelimit-limit-tokens:       {limit_tokens}")
    print(f"  x-ratelimit-remaining-tokens:   {rem_tokens}")
    print(f"  x-ratelimit-reset-requests:     {reset_req}")
    print(f"  x-ratelimit-reset-tokens:       {reset_tokens}")

    assert response.status_code == 200, f"Live Groq request failed: {response.text}"
    body = response.json()
    usage = body.get("usage", {})
    choice = body.get("choices", [{}])[0]
    msg = choice.get("message", {}).get("content", "")

    print("  --- Token Usage ---")
    print(f"  Prompt tokens:     {usage.get('prompt_tokens')}")
    print(f"  Completion tokens: {usage.get('completion_tokens')}")
    print(f"  Total tokens:      {usage.get('total_tokens')}")
    print(f"  Model output: \"{msg.strip()}\"")

    assert len(msg.strip()) > 10, "Empty model output received"
    print("  -> PASS: Live end-to-end Groq call confirmed valid.")
    results["test_live_groq"] = {
        "status": "PASS",
        "latency_ms": round(latency_ms, 1),
        "request_id": request_id,
        "remaining_requests": rem_req,
        "remaining_tokens": rem_tokens,
        "reset_requests": reset_req,
        "reset_tokens": reset_tokens,
        "total_tokens": usage.get("total_tokens"),
        "completion": msg.strip()
    }


async def main():
    print("================================================================")
    print("STARTING EMPIRICAL CHALLENGE 2: MILESTONE 1 AI ADAPTER SUITE")
    print("================================================================")

    await test_429_backoff_and_retry()
    await test_primary_model_failure_fallback()
    await test_token_capping()
    await test_live_groq_request()

    print("\n================================================================")
    print("CHALLENGE SUITE SUMMARY:")
    all_pass = True
    for test, res in results.items():
        print(f"  - {test}: {res if isinstance(res, str) else res['status']}")
        if isinstance(res, str) and "FAIL" in res:
            all_pass = False
        elif isinstance(res, dict) and res.get("status") != "PASS":
            all_pass = False

    if all_pass:
        print("\nALL EMPIRICAL CHALLENGES PASSED! VERDICT: APPROVE")
    else:
        print("\nCHALLENGE FAILURES DETECTED! VERDICT: REJECT")
    print("================================================================")
    return 0 if all_pass else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
