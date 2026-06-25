from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_qdrant_client, get_settings
from src.api.main import app


@pytest.fixture
def audit_client(mocker):
    mock_client = MagicMock()
    app.dependency_overrides[get_qdrant_client] = lambda: mock_client
    app.dependency_overrides[get_settings] = lambda: __import__(
        "src.api.dependencies", fromlist=["Settings"]
    ).Settings(qdrant_audit_collection="media_audit")
    yield TestClient(app), mock_client
    app.dependency_overrides.clear()


def test_get_audit_record_returns_payload(audit_client):
    client, mock_qdrant = audit_client
    point = MagicMock()
    point.payload = {"mediaHash": "abc", "authenticityScore": 0.9}
    mock_qdrant.retrieve.return_value = [point]

    resp = client.get("/api/audit/test-uuid")
    assert resp.status_code == 200
    assert resp.json()["mediaHash"] == "abc"


def test_get_audit_record_404_when_missing(audit_client):
    client, mock_qdrant = audit_client
    mock_qdrant.retrieve.return_value = []

    resp = client.get("/api/audit/missing-id")
    assert resp.status_code == 404
