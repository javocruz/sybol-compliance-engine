import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_status_returns_expected_keys(client, mocker):
    mocker.patch(
        "src.api.routes.status.get_sybol_client",
        return_value=mocker.Mock(is_configured=True),
    )
    mock_qdrant_cls = mocker.patch("qdrant_client.QdrantClient")
    mock_client = mock_qdrant_cls.return_value
    mock_client.get_collection.return_value = mocker.Mock(points_count=1795)

    resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["api"] == "ok"
    assert body["qdrant"] == "ok"
    assert body["regulations_chunks"] == 1795
    assert body["sybol_configured"] is True
    assert "model_loaded" in body
    assert "rag_index_loaded" in body
