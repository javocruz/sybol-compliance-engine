"""Tests for GET /api/regulations/{filename}."""

from fastapi.testclient import TestClient

from src.api.main import app


def test_serve_known_regulation_pdf():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/regulations/gdpr.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_unknown_regulation_returns_404():
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/regulations/not_a_real_file.pdf")

    assert response.status_code == 404
