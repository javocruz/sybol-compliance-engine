"""Unit tests for GET /api/audit endpoints."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_qdrant_client, get_settings
from src.api.main import app

SAMPLE_RECORD = {
    "id": "abc-123",
    "credential_id": "urn:uuid:abc-123",
    "evidence_url": "http://localhost:6333/collections/media_audit/points/abc-123",
    "media_hash": "deadbeef001122",
    "authenticity_score": 0.75,
    "score_breakdown": {"m": 0.8, "a": 0.7, "v": 0.75, "p": 0.75},
    "compliance_status": "review",
    "model_version": "v1.0",
    "analysis_timestamp": "2026-06-25T12:00:00Z",
    "regulation_refs": [
        {
            "regulation": "AI Act",
            "article": "13",
            "url": "https://eur-lex.europa.eu/aiact",
        }
    ],
}


@pytest.fixture
def mock_qdrant():
    return MagicMock()


@pytest.fixture
def client(mock_qdrant):
    app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant
    app.dependency_overrides[get_settings] = lambda: get_settings()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_audit_records_returns_empty_when_collection_missing(client, mocker):
    mocker.patch(
        "src.api.routes.audit.list_audit_records",
        return_value=([], 0),
    )
    response = client.get("/api/audit")
    assert response.status_code == 200
    body = response.json()
    assert body["records"] == []
    assert body["total"] == 0


def test_list_audit_records_returns_records(client, mocker):
    mocker.patch(
        "src.api.routes.audit.list_audit_records",
        return_value=([SAMPLE_RECORD], 1),
    )
    response = client.get("/api/audit")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["records"][0]["id"] == "abc-123"
    assert body["records"][0]["media_hash"] == "deadbeef001122"


def test_get_audit_record_returns_404_when_missing(client, mocker):
    mocker.patch("src.api.routes.audit.get_audit_record", return_value=None)
    response = client.get("/api/audit/missing-id")
    assert response.status_code == 404


def test_get_audit_record_returns_record(client, mocker):
    mocker.patch("src.api.routes.audit.get_audit_record", return_value=SAMPLE_RECORD)
    response = client.get("/api/audit/abc-123")
    assert response.status_code == 200
    body = response.json()
    assert body["credential_id"] == "urn:uuid:abc-123"
    assert body["compliance_status"] == "review"


def test_list_audit_records_returns_503_on_qdrant_error(client, mocker):
    mocker.patch(
        "src.api.routes.audit.list_audit_records",
        side_effect=RuntimeError("connection refused"),
    )
    response = client.get("/api/audit")
    assert response.status_code == 503
