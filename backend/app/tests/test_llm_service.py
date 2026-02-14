"""Tests for LLM service. Mocks Ollama/Anthropic; no real network calls."""

import json
from unittest.mock import patch

import httpx
import pytest

from app.exceptions import ExternalServiceError
from app.services import llm_service


def test_call_ollama_valid_json():
    raw = json.dumps({"pain_point": "Slow search", "topic": "search", "urgency": "high"})
    with patch.object(llm_service, "_call_ollama", return_value=raw):
        result, raw_out = llm_service.call_llm("user", "system", temperature=0)
    assert result["pain_point"] == "Slow search"
    assert result["topic"] == "search"
    assert raw_out == raw


def test_call_ollama_strips_markdown_fences():
    inner = '{"pain_point": "x", "topic": "y", "urgency": "low"}'
    raw = f"```json\n{inner}\n```"
    with patch.object(llm_service, "_call_ollama", return_value=raw):
        result, _ = llm_service.call_llm("user", "system", temperature=0)
    assert result["pain_point"] == "x"
    assert result["topic"] == "y"


def test_call_ollama_invalid_json_retries_then_raises():
    with patch.object(llm_service, "_call_ollama") as m:
        m.return_value = "not json at all"
        with pytest.raises(ExternalServiceError) as exc_info:
            llm_service.call_llm("user", "system", temperature=0)
    assert "invalid" in str(exc_info.value.message).lower() or "JSON" in str(exc_info.value)


def test_call_ollama_empty_response_raises():
    with patch.object(llm_service, "_call_ollama", return_value=""):
        with pytest.raises(ExternalServiceError):
            llm_service.call_llm("user", "system", temperature=0)


def test_unknown_provider_raises():
    with patch.object(llm_service.settings, "llm_provider", "unknown"):
        with pytest.raises(ExternalServiceError) as exc_info:
            llm_service.call_llm("user", "system", temperature=0)
    msg = str(exc_info.value.message).lower()
    assert "unknown" in msg or "provider" in msg


def test_call_ollama_timeout_raises_external_service_error():
    with patch.object(llm_service, "_call_ollama", side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(ExternalServiceError):
            llm_service.call_llm("user", "system", temperature=0)
