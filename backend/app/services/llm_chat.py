"""
Chat-specific LLM calls. call_chat_llm() for conversational flow with optional tool use.
Uses chat_llm_model and chat_timeout_seconds. No JSON format.
"""

import json
import re
import time

import httpx

from app.config import settings
from app.exceptions import ExternalServiceError
from app.utils.logging import get_logger

logger = get_logger(__name__)

ChatResult = tuple[str, list[dict]]


def _ollama_messages_to_api(messages: list[dict]) -> list[dict]:
    """Convert chat messages to Ollama format (role + content string)."""
    out = []
    for m in messages:
        role, content = m.get("role", "user"), m.get("content", "")
        if isinstance(content, list):
            parts = [c.get("text", c.get("content", "")) for c in content if c.get("type") in ("text", "tool_result")]
            content = "\n\n".join(p for p in parts if p)
        out.append({"role": role, "content": content or " "})
    return out


def _call_ollama_chat(
    system_prompt: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> ChatResult:
    """Ollama /api/chat with messages array. No JSON format. Parse tool calls from response if present."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    ollama_msgs = _ollama_messages_to_api(messages)
    payload = {
        "model": settings.chat_llm_model,
        "messages": [{"role": "system", "content": system_prompt}] + ollama_msgs,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    with httpx.Client(timeout=settings.chat_timeout_seconds) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
    data = resp.json()
    content = (data.get("message") or {}).get("content") or ""
    text = content.strip()
    tool_calls: list[dict] = []
    match = re.search(r'\{[^{}]*"tool"\s*:\s*"[^"]+"[^{}]*"params"\s*:[^{}]*\}', text)
    if match:
        try:
            obj = json.loads(match.group(0))
            if "tool" in obj and "params" in obj:
                tool_calls.append({"tool": obj["tool"], "params": obj.get("params", {})})
        except json.JSONDecodeError:
            pass
    return text, tool_calls


def _call_anthropic_chat(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict] | None,
    temperature: float,
    max_tokens: int,
) -> ChatResult:
    """Anthropic messages.create with tools. Parse tool_use blocks; return (text, tool_calls)."""
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.anthropic_api_key or "dummy")
    kwargs = {
        "model": settings.chat_llm_model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
    msg = client.messages.create(**kwargs)
    text_parts = []
    tool_calls: list[dict] = []
    for block in (msg.content or []):
        if getattr(block, "type", None) == "text":
            text_parts.append(getattr(block, "text", "") or "")
        elif getattr(block, "type", None) == "tool_use":
            tool_calls.append({
                "id": getattr(block, "id", ""),
                "name": getattr(block, "name", ""),
                "input": getattr(block, "input", None) or {},
            })
    return "\n".join(text_parts).strip(), tool_calls


def call_chat_llm(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ChatResult:
    """
    Chat LLM: message array, optional tools. Returns (response_text, tool_calls_list).
    Uses chat_llm_model and chat_timeout_seconds. No JSON format.
    """
    temperature = temperature if temperature is not None else settings.chat_temperature
    max_tokens = max_tokens if max_tokens is not None else settings.chat_max_response_tokens
    provider = (settings.llm_provider or "ollama").lower()
    start = time.perf_counter()
    try:
        if provider == "ollama":
            text, tool_calls = _call_ollama_chat(system_prompt, messages, temperature, max_tokens)
        elif provider == "anthropic":
            text, tool_calls = _call_anthropic_chat(system_prompt, messages, tools, temperature, max_tokens)
        else:
            raise ExternalServiceError(f"Unknown LLM_PROVIDER: {provider}")
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "Chat LLM call succeeded",
            extra={"provider": provider, "duration_ms": duration_ms, "tool_calls": len(tool_calls)},
        )
        return text, tool_calls
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.error("Chat LLM request failed", extra={"provider": provider, "duration_ms": duration_ms, "error": str(e)})
        raise ExternalServiceError("Chat LLM request failed.", details={"error": str(e)}) from e


def call_brief_llm(system_prompt: str, user_content: str) -> str:
    """
    Single-turn LLM call for brief section generation. Uses brief_llm_model, brief_timeout_seconds,
    brief_temperature, brief_max_section_tokens. Returns raw text (markdown).
    """
    model = getattr(settings, "brief_llm_model", settings.chat_llm_model)
    timeout = getattr(settings, "brief_timeout_seconds", 60)
    temperature = getattr(settings, "brief_temperature", 0.4)
    max_tokens = getattr(settings, "brief_max_section_tokens", 1000)
    messages = [{"role": "user", "content": user_content}]
    provider = (settings.llm_provider or "ollama").lower()
    start = time.perf_counter()
    try:
        if provider == "ollama":
            url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}] + _ollama_messages_to_api(messages),
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
            data = resp.json()
            text = (data.get("message") or {}).get("content") or ""
        elif provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.anthropic_api_key or "dummy")
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
                temperature=temperature,
            )
            text = ""
            for block in (msg.content or []):
                if getattr(block, "type", None) == "text":
                    text += getattr(block, "text", "") or ""
        else:
            raise ExternalServiceError(f"Unknown LLM_PROVIDER: {provider}")
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("Brief LLM call succeeded", extra={"model": model, "duration_ms": duration_ms})
        return text.strip()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error("Brief LLM request failed", extra={"model": model, "error": str(e)})
        raise ExternalServiceError("Brief LLM request failed.", details={"error": str(e)}) from e


def call_spec_llm(system_prompt: str, user_content: str) -> str:
    """
    Single-turn LLM call for spec section generation. Uses spec_llm_model, spec_timeout_seconds,
    spec_temperature, spec_max_section_tokens. Returns raw text (markdown).
    """
    model = getattr(settings, "spec_llm_model", settings.chat_llm_model)
    timeout = getattr(settings, "spec_timeout_seconds", 60)
    temperature = getattr(settings, "spec_temperature", 0.3)
    max_tokens = getattr(settings, "spec_max_section_tokens", 1500)
    messages = [{"role": "user", "content": user_content}]
    provider = (settings.llm_provider or "ollama").lower()
    start = time.perf_counter()
    try:
        if provider == "ollama":
            url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}] + _ollama_messages_to_api(messages),
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
            data = resp.json()
            text = (data.get("message") or {}).get("content") or ""
        elif provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=settings.anthropic_api_key or "dummy")
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
                temperature=temperature,
            )
            text = ""
            for block in (msg.content or []):
                if getattr(block, "type", None) == "text":
                    text += getattr(block, "text", "") or ""
        else:
            raise ExternalServiceError(f"Unknown LLM_PROVIDER: {provider}")
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("Spec LLM call succeeded", extra={"model": model, "duration_ms": duration_ms})
        return text.strip()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error("Spec LLM request failed", extra={"model": model, "error": str(e)})
        raise ExternalServiceError("Spec LLM request failed.", details={"error": str(e)}) from e
