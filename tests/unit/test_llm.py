"""Unit tests for synthesis LLM factory."""

import os
from unittest.mock import MagicMock, patch

import pytest

from rag.llm import (
    check_ollama_available,
    get_model_name,
    get_ollama_model,
    get_synthesis_llm,
    normalize_provider,
    resolve_provider,
)


def test_normalize_provider_ollama():
    assert normalize_provider("ollama") == "ollama"


def test_normalize_provider_mistral_and_unknown():
    assert normalize_provider("mistral") == "mistral"
    assert normalize_provider("invalid") == "mistral"


def test_get_model_name():
    assert get_model_name("mistral") == "mistral-large-latest"
    assert get_model_name("ollama") == get_ollama_model()


def test_resolve_provider_falls_back_to_ollama_without_key(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    assert resolve_provider("mistral") == "ollama"


def test_get_synthesis_llm_mistral_requires_api_key(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(ValueError, match="MISTRAL_API_KEY"):
        get_synthesis_llm("mistral")


def test_get_synthesis_llm_mistral(env_vars):
    with patch("rag.llm.MistralAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        llm = get_synthesis_llm("mistral")
        mock_cls.assert_called_once()
        assert llm is mock_cls.return_value


def test_get_synthesis_llm_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    with patch("llama_index.llms.ollama.Ollama") as mock_cls:
        mock_cls.return_value = MagicMock()
        llm = get_synthesis_llm("ollama")
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["model"] == "qwen2.5:7b-instruct"
        assert llm is mock_cls.return_value


def test_check_ollama_available_connect_error(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:59999")

    ok, detail = check_ollama_available()
    assert ok is False
    assert detail is not None
    assert "not reachable" in detail


def test_check_ollama_available_ok(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "models": [{"name": "qwen2.5:7b-instruct"}],
    }

    with patch("rag.llm.httpx.get", return_value=mock_response):
        ok, detail = check_ollama_available()

    assert ok is True
    assert detail is None
