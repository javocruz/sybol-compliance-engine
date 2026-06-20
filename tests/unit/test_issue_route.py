"""
Integration-level unit tests for POST /api/issue.

All heavy dependencies (score_image, query_regulations, write_audit_record,
SybolClient, get_index, get_qdrant_client, get_settings, get_sybol_client)
are patched so the test suite runs without live infrastructure.
"""

import io
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.api.dependencies import (
    get_index,
    get_qdrant_client,
    get_settings,
    get_sybol_client,
)
from src.api.main import app
from src.credentials.sybol_client import SybolClient, SybolSigningError
from src.rag.models import ComplianceResult, RegulationRef
from src.scoring.models import ComplianceStatus, ScoringResult, SignalBreakdown

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def png_bytes():
    image = Image.new("RGB", (64, 64), color=(100, 150, 200))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def mock_scoring_result():
    return ScoringResult(
        authenticity_score=0.85,
        score_breakdown=SignalBreakdown(m=0.9, a=0.8, v=0.85, p=0.85),
        compliance_status=ComplianceStatus.COMPLIANT,
        media_hash="deadbeef001122",
        model_version="v1.0",
    )


@pytest.fixture
def mock_rag_result():
    return ComplianceResult(
        summary="No violations.",
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


@pytest.fixture
def mock_qdrant():
    client = MagicMock()
    client.get_collections.return_value.collections = [MagicMock(name="media_audit")]
    for c in client.get_collections.return_value.collections:
        c.name = "media_audit"
    return client


@pytest.fixture
def mock_settings():
    from src.api.dependencies import Settings

    return Settings(
        qdrant_url="http://localhost:6333",
        qdrant_audit_collection="media_audit",
        sybol_document_id="doc-uuid",
        sybol_issuer_key="kms-key",
    )


SIGNED_VC = {
    "id": "credential-jti",
    "signed_token": "eyJhbGciOiJFUzI1NiJ9...",
    "issuer": "did:sybol:tenant123:issuer",
}


def _configured_sybol_client():
    client = MagicMock(spec=SybolClient)
    client.is_configured = True
    client.issue_credential.return_value = SIGNED_VC
    return client


def _unconfigured_sybol_client():
    client = MagicMock(spec=SybolClient)
    client.is_configured = False
    return client


# ---------------------------------------------------------------------------
# Helper: build a client with all deps overridden
# ---------------------------------------------------------------------------


def _make_test_client(
    mocker,
    scoring_result,
    rag_result,
    mock_index,
    mock_qdrant,
    mock_settings,
    sybol_client,
    evidence_url="http://localhost:6333/collections/media_audit/points/abc",
):
    mocker.patch("src.api.routes.issue.score_image", return_value=scoring_result)
    mocker.patch("src.api.routes.issue.query_regulations", return_value=rag_result)
    mocker.patch("src.api.routes.issue.write_audit_record", return_value=evidence_url)

    app.dependency_overrides[get_index] = lambda: mock_index
    app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_sybol_client] = lambda: sybol_client

    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_503_when_sybol_not_configured(
    mocker,
    png_bytes,
    mock_scoring_result,
    mock_rag_result,
    mock_index,
    mock_qdrant,
    mock_settings,
):
    try:
        client = _make_test_client(
            mocker,
            mock_scoring_result,
            mock_rag_result,
            mock_index,
            mock_qdrant,
            mock_settings,
            _unconfigured_sybol_client(),
        )
        response = client.post(
            "/api/issue",
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_returns_signed_vc_on_success(
    mocker,
    png_bytes,
    mock_scoring_result,
    mock_rag_result,
    mock_index,
    mock_qdrant,
    mock_settings,
):
    try:
        client = _make_test_client(
            mocker,
            mock_scoring_result,
            mock_rag_result,
            mock_index,
            mock_qdrant,
            mock_settings,
            _configured_sybol_client(),
        )
        response = client.post(
            "/api/issue",
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "signed_vc_issued"
        assert body["signed"] is True
        assert body["signed_vc"]["signed_token"].startswith("eyJ")
        assert body["vc_payload"] is not None
    finally:
        app.dependency_overrides.clear()


def test_returns_502_when_signing_fails(
    mocker,
    png_bytes,
    mock_scoring_result,
    mock_rag_result,
    mock_index,
    mock_qdrant,
    mock_settings,
):
    sybol = MagicMock(spec=SybolClient)
    sybol.is_configured = True
    sybol.issue_credential.side_effect = SybolSigningError(
        "Sybol API returned 500: internal error"
    )

    try:
        client = _make_test_client(
            mocker,
            mock_scoring_result,
            mock_rag_result,
            mock_index,
            mock_qdrant,
            mock_settings,
            sybol,
        )
        response = client.post(
            "/api/issue",
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert response.status_code == 502
        assert "500" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_returns_400_for_unsupported_file_type(
    mocker, mock_scoring_result, mock_rag_result, mock_index, mock_qdrant, mock_settings
):
    try:
        client = _make_test_client(
            mocker,
            mock_scoring_result,
            mock_rag_result,
            mock_index,
            mock_qdrant,
            mock_settings,
            _configured_sybol_client(),
        )
        response = client.post(
            "/api/issue",
            files={"file": ("test.gif", b"GIF89a...", "image/gif")},
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_returns_503_when_rag_fails(
    mocker,
    png_bytes,
    mock_scoring_result,
    mock_index,
    mock_qdrant,
    mock_settings,
):
    mocker.patch("src.api.routes.issue.score_image", return_value=mock_scoring_result)
    mocker.patch(
        "src.api.routes.issue.query_regulations",
        side_effect=TimeoutError("Mistral request timed out"),
    )

    app.dependency_overrides[get_index] = lambda: mock_index
    app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_sybol_client] = lambda: _configured_sybol_client()

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/issue",
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert response.status_code == 503
        assert "rag pipeline failed" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_returns_503_when_audit_write_fails(
    mocker,
    png_bytes,
    mock_scoring_result,
    mock_rag_result,
    mock_index,
    mock_qdrant,
    mock_settings,
):
    mocker.patch("src.api.routes.issue.score_image", return_value=mock_scoring_result)
    mocker.patch("src.api.routes.issue.query_regulations", return_value=mock_rag_result)
    mocker.patch(
        "src.api.routes.issue.write_audit_record",
        side_effect=Exception("Qdrant is down"),
    )

    app.dependency_overrides[get_index] = lambda: mock_index
    app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_sybol_client] = lambda: _configured_sybol_client()

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/issue",
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert response.status_code == 503
        assert "qdrant" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
