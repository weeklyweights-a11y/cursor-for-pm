"""
Provider-agnostic LLM service. call_llm() for extraction (JSON). call_chat_llm() for chat (text + optional tool calls).
Supports Ollama (local) and Anthropic (API). No domain logic.
"""

import json
import re
import time

import httpx

from app.config import settings
from app.exceptions import ExternalServiceError
from app.utils.logging import get_logger

logger = get_logger(__name__)

def _strip_markdown_fences(raw: str) -> str:
    """Remove markdown code fences (```json ... ```) if present."""
    stripped = raw.strip()
    match = re.search(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


def _parse_json_response(raw: str) -> dict:
    """Parse raw string as JSON. Strip markdown fences if needed. Raises ValueError on failure."""
    stripped = _strip_markdown_fences(raw)
    return json.loads(stripped)


def _call_ollama(
    system_prompt: str, prompt: str, temperature: float, max_tokens: int, use_json_format: bool = True
) -> str:
    """Call Ollama /api/chat. Returns the message content text. Skip format=json (many Ollama setups 500 with it); we parse JSON from raw text."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    # Do not use "format": "json" - Ollama often returns 500. Prompt asks for JSON; we parse via _strip_markdown_fences + json.loads.
    with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
    data = resp.json()
    message = data.get("message") or {}
    return (message.get("content") or "").strip()


def _call_anthropic(system_prompt: str, prompt: str, temperature: float, max_tokens: int) -> str:
    """Call Anthropic API. Returns the text content. Imports anthropic only when used."""
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.anthropic_api_key or "dummy")
    msg = client.messages.create(
        model=settings.anthropic_extraction_model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    if not msg.content or not hasattr(msg.content[0], "text"):
        return ""
    return msg.content[0].text.strip()


def call_chat_llm(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
):
    """Delegate to llm_chat for chat flow. Kept here for import compatibility."""
    from app.services.llm_chat import call_chat_llm as _call_chat_llm
    return _call_chat_llm(system_prompt, messages, tools, temperature, max_tokens)


def call_llm(
    prompt: str,
    system_prompt: str,
    expected_schema: dict | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> tuple[dict, str]:
    """
    Call the configured LLM and return (parsed JSON, raw response text). Retries on parse failure
    up to LLM_MAX_RETRIES. Raises ExternalServiceError on timeout, non-2xx, or after retries exhausted.
    """
    provider = (settings.llm_provider or "ollama").lower()
    model = settings.ollama_model if provider == "ollama" else settings.anthropic_extraction_model
    prompt_len = len(prompt) + len(system_prompt)
    start = time.perf_counter()
    last_raw = ""
    last_error = None

    for attempt in range(settings.llm_max_retries + 1):
        try:
            if provider == "ollama":
                raw = _call_ollama(system_prompt, prompt, temperature, max_tokens)
            elif provider == "anthropic":
                raw = _call_anthropic(system_prompt, prompt, temperature, max_tokens)
            else:
                raise ExternalServiceError(f"Unknown LLM_PROVIDER: {provider}")

            last_raw = raw
            if not raw:
                raise ValueError("Empty response")

            result = _parse_json_response(raw)
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "LLM call succeeded",
                extra={
                    "provider": provider,
                    "model": model,
                    "duration_ms": duration_ms,
                    "prompt_length": prompt_len,
                },
            )
            return result, raw

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            if attempt < settings.llm_max_retries:
                continue
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "LLM response invalid after retries",
                extra={
                    "provider": provider,
                    "model": model,
                    "duration_ms": duration_ms,
                    "raw_preview": (last_raw or "")[:500],
                },
            )
            raise ExternalServiceError(
                "LLM returned invalid JSON after retries.",
                details={"raw_preview": (last_raw or "")[:500]},
            ) from e
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "LLM request failed",
                extra={"provider": provider, "model": model, "duration_ms": duration_ms, "error": str(e)},
            )
            raise ExternalServiceError("LLM request failed.", details={"error": str(e)}) from e

    raise ExternalServiceError("LLM call failed.", details={}) from last_error
