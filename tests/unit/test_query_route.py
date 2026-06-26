"""Unit tests for POST /api/query."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_index
from src.api.main import app
from src.rag.models import ComplianceResult, RegulationRef


@pytest.fixture
def mock_compliance_result():
    return ComplianceResult(
        summary="GDPR Article 5 requires lawful processing.",
        regulationRefs=[
            RegulationRef(
                regulation="GDPR",
                article="5",
                sourceUrl="https://eur-lex.europa.eu/gdpr",
                excerpt="Article 5 requires lawful processing.",
            )
        ],
    )


@pytest.fixture
def mock_index():
    return MagicMock()


def test_query_returns_structured_regulation_refs(
    mocker, mock_index, mock_compliance_result
):
    mocker.patch(
        "src.api.routes.query.query_regulations",
        return_value=mock_compliance_result,
    )
    app.dependency_overrides[get_index] = lambda: mock_index

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/query",
            json={"question": "What GDPR articles apply to data processing?"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "GDPR Article 5 requires lawful processing."
        assert body["llm_provider"] == "mistral"
        assert body["llm_model"] == "mistral-large-latest"
        assert len(body["regulation_refs"]) == 1
        ref = body["regulation_refs"][0]
        assert ref["regulation"] == "GDPR"
        assert ref["article"] == "5"
        assert ref["url"] == "https://eur-lex.europa.eu/gdpr"
        assert "sourceUrl" not in ref
    finally:
        app.dependency_overrides.clear()


def test_query_calls_query_regulations_with_question_and_provider(
    mocker, mock_index, mock_compliance_result
):
    mocker.patch(
        "src.api.routes.query.check_ollama_available",
        return_value=(True, None),
    )
    mock_query = mocker.patch(
        "src.api.routes.query.query_regulations",
        return_value=mock_compliance_result,
    )
    app.dependency_overrides[get_index] = lambda: mock_index

    try:
        client = TestClient(app, raise_server_exceptions=False)
        client.post(
            "/api/query",
            json={
                "question": "AI transparency requirements",
                "llm_provider": "ollama",
            },
        )

        mock_query.assert_called_once_with(
            "AI transparency requirements",
            mock_index,
            llm_provider="ollama",
        )
    finally:
        app.dependency_overrides.clear()


def test_query_ollama_response_includes_model_name(
    mocker, mock_index, mock_compliance_result, monkeypatch
):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    mocker.patch(
        "src.api.routes.query.check_ollama_available",
        return_value=(True, None),
    )
    mocker.patch(
        "src.api.routes.query.query_regulations",
        return_value=mock_compliance_result,
    )
    app.dependency_overrides[get_index] = lambda: mock_index

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/query",
            json={"question": "test", "llm_provider": "ollama"},
        )
        body = response.json()
        assert body["llm_provider"] == "ollama"
        assert body["llm_model"] == "qwen2.5:7b-instruct"
    finally:
        app.dependency_overrides.clear()


def test_query_returns_503_when_mistral_not_configured(mocker, mock_index, monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    app.dependency_overrides[get_index] = lambda: mock_index

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/query",
            json={"question": "test", "llm_provider": "mistral"},
        )
        assert response.status_code == 503
        assert "MISTRAL_API_KEY" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_query_returns_503_when_ollama_unavailable(mocker, mock_index):
    mocker.patch(
        "src.api.routes.query.check_ollama_available",
        return_value=(False, "Ollama is not reachable at http://localhost:11434."),
    )
    app.dependency_overrides[get_index] = lambda: mock_index

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/query",
            json={"question": "test", "llm_provider": "ollama"},
        )
        assert response.status_code == 503
        assert "Ollama" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_query_returns_503_when_index_unavailable(mocker):
    from fastapi import HTTPException

    def raise_503():
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline not available.",
        )

    app.dependency_overrides[get_index] = raise_503

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/query",
            json={"question": "test"},
        )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()
