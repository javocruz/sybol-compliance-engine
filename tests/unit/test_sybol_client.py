from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.credentials.sybol_client import (
    DEFAULT_API_BASE_URL,
    SybolClient,
    SybolNotConfiguredError,
    SybolSigningError,
)

VALID_ACCESS = "access-token-abc"
VALID_ID = "id-token-xyz"
DOC_ID = "catalog-doc-uuid"
ISSUER_KEY = "kms-key-1"

ISSUE_REQUEST = {
    "documentId": DOC_ID,
    "issuerKey": ISSUER_KEY,
    "subject": "urn:media:abc123",
    "claims": [{"key": "mediaHash", "value": "abc123"}],
    "format": "w3c-vc",
}

SIGNED_CREDENTIAL = {
    "id": "credential-jti",
    "signed_token": "eyJhbGciOiJFUzI1NiJ9...",
    "status": "issued",
    "issuer": "did:web:sybol.id",
}


def _client(**kwargs):
    defaults = {
        "api_base_url": DEFAULT_API_BASE_URL,
        "access_token": VALID_ACCESS,
        "id_token": VALID_ID,
        "document_id": DOC_ID,
        "issuer_key": ISSUER_KEY,
    }
    defaults.update(kwargs)
    return SybolClient(**defaults)


def test_is_configured_with_tokens_and_catalog():
    assert _client().is_configured is True


def test_not_configured_without_document_id():
    assert _client(document_id=None).is_configured is False


def test_not_configured_without_issuer_key():
    assert _client(issuer_key=None).is_configured is False


def test_not_configured_without_auth():
    assert _client(access_token=None, id_token=None, email=None, password=None).is_configured is False


def test_configured_with_email_password_and_catalog():
    assert _client(
        access_token=None,
        id_token=None,
        email="user@ie.id",
        password="secret",
    ).is_configured is True


def test_login_stores_tokens():
    client = _client(access_token=None, id_token=None, email="user@ie.id", password="secret")
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "success": True,
        "data": {
            "accessToken": VALID_ACCESS,
            "idToken": VALID_ID,
            "refreshToken": "refresh",
        },
    }

    with patch("httpx.post", return_value=mock_response) as post:
        data = client.login()

    assert data["accessToken"] == VALID_ACCESS
    assert client._access_token == VALID_ACCESS
    assert client._id_token == VALID_ID
    post.assert_called_once()
    assert post.call_args[0][0].endswith("/auth/login")


def test_issue_credential_success():
    client = _client()
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"success": True, "data": SIGNED_CREDENTIAL}

    with patch("httpx.request", return_value=mock_response):
        result = client.issue_credential(ISSUE_REQUEST)

    assert result["signed_token"] == SIGNED_CREDENTIAL["signed_token"]


def test_issue_raises_on_missing_signed_token():
    client = _client()
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"success": True, "data": {"id": "x"}}

    with patch("httpx.request", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="signed credential"):
            client.issue_credential(ISSUE_REQUEST)


def test_issue_raises_on_api_error():
    client = _client()
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 422
    mock_response.text = "validation failed"
    mock_response.json.return_value = {"success": False, "message": "invalid claims"}

    with patch("httpx.request", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="422"):
            client.issue_credential(ISSUE_REQUEST)


def test_login_timeout():
    client = _client(access_token=None, id_token=None, email="a@b.com", password="x")
    with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(SybolSigningError, match="timed out"):
            client.login()
