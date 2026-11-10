import json
import re
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.services.text_sanitize import sanitize_prose


class IncompleteGenerationError(RuntimeError):
    """The provider stopped before finishing a complete answer."""


class LLMUnavailableError(RuntimeError):
    """The configured LLM provider is temporarily unavailable or rate limited."""


_TRANSIENT_PROVIDER_MARKERS = (
    "model is unloaded",
    "unloaded",
    "has not started loading",
    "failed to load model",
    "engine protocol startup was aborted",
    "terminated",
    "loading",
)


def _parse_retry_after(headers: httpx.Headers, default: float = 2.0) -> float:
    """Extracts delay in seconds from HTTP 429 headers."""
    val = headers.get("retry-after")
    if val:
        try:
            return max(0.5, min(float(val), 15.0))
        except ValueError:
            pass
    # Groq rate limit reset headers: e.g. '615ms', '1.2s'
    for header_name in ("x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        val = headers.get(header_name)
        if val:
            val_str = str(val).strip().lower()
            if val_str.endswith("ms"):
                try:
                    return max(0.2, min(float(val_str[:-2]) / 1000.0, 15.0))
                except ValueError:
                    pass
            elif val_str.endswith("s"):
                try:
                    return max(0.5, min(float(val_str[:-1]), 15.0))
                except ValueError:
                    pass
    return default


class AIProviderService:
    def __init__(self):
        self.provider = getattr(settings, "LLM_PROVIDER", "groq").lower()
        self.api_key = getattr(settings, "GROQ_API_KEY", None)

        # Chat configuration
        raw_base_url = settings.LLM_BASE_URL.rstrip("/")
        if self.provider == "groq":
            if "127.0.0.1" in raw_base_url or "localhost" in raw_base_url:
                self.chat_base_url = "https://api.groq.com/openai/v1"
            else:
                self.chat_base_url = raw_base_url
            if "gemma" in settings.LLM_MODEL.lower():
                self.chat_model = "openai/gpt-oss-120b"
            else:
                self.chat_model = settings.LLM_MODEL
        else:
            self.chat_base_url = raw_base_url
            self.chat_model = settings.LLM_MODEL

        self.fallback_model = getattr(settings, "LLM_FALLBACK_MODEL", None)
        self.base_url = self.chat_base_url  # backwards compatibility

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        key = self.api_key or getattr(settings, "GROQ_API_KEY", None)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def check_health(self) -> Dict[str, Any]:
        """Probes the configured chat provider's model list. Never exposes keys."""
        status: Dict[str, Any] = {
            "provider": self.provider,
            "chat_model": self.chat_model,
            "chat_ready": False,
            "error": None,
        }
        try:
            timeout = httpx.Timeout(5.0, connect=3.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                models_resp = await client.get(
                    f"{self.chat_base_url}/models",
                    headers=self._auth_headers(),
                )
                status["chat_ready"] = models_resp.status_code == 200
                if not status["chat_ready"]:
                    status["error"] = f"HTTP {models_resp.status_code}"
        except Exception as exc:
            status["error"] = type(exc).__name__
        return status

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        response_format: Optional[Dict[str, Any]] = None,
        require_complete: bool = False,
    ) -> str:
        """Sends chat completion request with Bearer auth, timeout, 429 backoff & model fallback."""
        url = f"{self.chat_base_url}/chat/completions"
        effective_max_tokens = min(max_tokens or 1500, 1500)
        headers = self._auth_headers()
        timeout = httpx.Timeout(120.0, connect=10.0)

        # Helper to execute a chat post with retry
        async def _execute_with_model(target_model: str, is_fallback: bool = False) -> Optional[httpx.Response]:
            payload: Dict[str, Any] = {
                "model": target_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": effective_max_tokens,
            }
            if response_format:
                payload["response_format"] = response_format

            resp = None
            rate_limit_retries = 2
            for attempt in range(rate_limit_retries + 1):
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        try:
                            resp = await client.post(url, headers=headers, json=payload)
                        except TypeError:
                            resp = await client.post(url, json=payload)
                except httpx.HTTPError:
                    resp = None

                if resp is not None:
                    if resp.status_code == 200:
                        return resp
                    if resp.status_code == 429 and attempt < rate_limit_retries:
                        retry_after = _parse_retry_after(resp.headers, default=2.0 * (attempt + 1))
                        await asyncio.sleep(retry_after)
                        continue
                    if _is_transient_response(resp) and attempt < rate_limit_retries:
                        await asyncio.sleep(2.0 * (attempt + 1))
                        continue
                elif attempt < rate_limit_retries:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue

            return resp

        # 1. Primary Model Attempt
        resp = await _execute_with_model(self.chat_model)

        # 2. If 429 or failure persists, attempt Fallback Model
        if (resp is None or resp.status_code in (404, 429, 500, 502, 503, 504)) and self.fallback_model and self.fallback_model != self.chat_model:
            resp = await _execute_with_model(self.fallback_model, is_fallback=True)

        if resp is None or resp.status_code != 200:
            status_code = resp.status_code if resp is not None else "unreachable"
            body = resp.text if resp is not None else ""
            if resp is not None and resp.status_code == 429:
                raise LLMUnavailableError(
                    "AI tutor is currently experiencing high demand. Please try again in a few moments."
                )
            raise RuntimeError(
                f"LLM chat completion failed with status {status_code}: {body}"
            )

        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content") or ""
        if not content.strip() and "reasoning_content" in message:
            content = message["reasoning_content"]

        if response_format:
            return content.strip()

        cleaned = _clean_generated_text(content)
        if not _is_complete_prose(cleaned):
            last_punct = max(cleaned.rfind("."), cleaned.rfind("!"), cleaned.rfind("?"))
            if last_punct > 40:
                cleaned = cleaned[: last_punct + 1].strip()

        if require_complete and not _is_complete_prose(cleaned):
            raise IncompleteGenerationError("The model stopped before finishing its answer.")
        if not cleaned:
            raise IncompleteGenerationError("The model returned an empty answer.")

        return cleaned


_GENERATED_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _is_transient_response(response: httpx.Response) -> bool:
    if response.status_code >= 500:
        return True
    if response.status_code != 400:
        return False
    body = (response.text or "").lower()
    return any(marker in body for marker in _TRANSIENT_PROVIDER_MARKERS)


def _clean_generated_text(text: str) -> str:
    """Removes corrupt bytes, control characters and LaTeX/markdown artifacts."""
    cleaned = str(text).replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"\ufffd\?*", " ", cleaned)
    cleaned = _GENERATED_CONTROL_CHARS.sub("", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return sanitize_prose(cleaned)


def _is_complete_prose(text: str) -> bool:
    """True when prose ends like a finished answer, not a cut-off sentence."""
    stripped = (text or "").rstrip()
    while stripped and stripped[-1] in "\"')]}’”":
        stripped = stripped[:-1].rstrip()
    if not stripped:
        return False
    return stripped[-1] in ".!?" or stripped[-1].isdigit()


ai_provider = AIProviderService()
