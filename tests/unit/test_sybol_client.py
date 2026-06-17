# TODO(Darius): Replace url=None with a valid URL in the test below once the Sybol API is available for testing.

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.credentials.sybol_client import (
    SybolClient,
    SybolNotConfiguredError,
    SybolSigningError,
)

VALID_URL = "https://api.sybol.io/api/bl/credentials"
VALID_ACCESS_TOKEN = "access-token-abc"
VALID_ID_TOKEN = "id-token-xyz"

UNSIGNED_PAYLOAD = {
    "@context": ["https://www.w3.org/2018/credentials/v1"],
    "id": "urn:uuid:abc",
    "type": ["VerifiableCredential", "MediaComplianceCredential"],
    "issuanceDate": "2026-06-14T12:00:00Z",
    "credentialSubject": {"id": "urn:media:deadbeef"},
}
SIGNED_VC = {
    **UNSIGNED_PAYLOAD,
    "issuer": "did:sybol:tenant123:issuer",
    "proof": {
        "type": "EcdsaSecp256k1Signature2019",
        "jws": "abc123",
    },
}
SUCCESS_ENVELOPE = {"success": True, "data": SIGNED_VC}


def _client(
    url=VALID_URL,
    access_token=VALID_ACCESS_TOKEN,
    id_token=VALID_ID_TOKEN,
    timeout=5.0,
):
    return SybolClient(
        api_url=url,
        access_token=access_token,
        id_token=id_token,
        timeout=timeout,
    )


# --- is_configured ---


def test_is_configured_true_when_all_set():
    assert _client().is_configured is True


def test_not_configured_when_url_missing():
    assert _client(url=None).is_configured is False


def test_not_configured_when_access_token_missing():
    assert _client(access_token=None).is_configured is False


def test_not_configured_when_id_token_missing():
    assert _client(id_token=None).is_configured is False


def test_not_configured_when_url_is_tbd_placeholder():
    assert (
        _client(url="TBD_pending_darius_confirmation_with_inigo").is_configured is False
    )


def test_not_configured_when_access_token_is_tbd_placeholder():
    assert (
        _client(access_token="TBD_pending_darius_confirmation_with_inigo").is_configured
        is False
    )


def test_not_configured_when_id_token_is_tbd_placeholder():
    assert (
        _client(id_token="TBD_pending_darius_confirmation_with_inigo").is_configured
        is False
    )


# --- sign_credential: not configured ---


def test_sign_raises_not_configured_when_url_missing():
    client = _client(url=None)
    with pytest.raises(SybolNotConfiguredError):
        client.sign_credential(UNSIGNED_PAYLOAD)


# --- sign_credential: success ---


def test_sign_returns_signed_vc_on_success():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = SUCCESS_ENVELOPE

    with patch(
        "src.credentials.sybol_client.httpx.post", return_value=mock_response
    ) as mock_post:
        result = _client().sign_credential(UNSIGNED_PAYLOAD)

    assert result["proof"]["type"] == "EcdsaSecp256k1Signature2019"
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["json"] == UNSIGNED_PAYLOAD
    headers = call_kwargs.kwargs["headers"]
    assert headers["Authorization"] == f"Bearer {VALID_ACCESS_TOKEN}"
    assert headers["x-id-token"] == VALID_ID_TOKEN


# --- sign_credential: HTTP errors ---


def test_sign_raises_on_non_2xx():
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 422
    mock_response.text = "Unprocessable entity"
    mock_response.json.return_value = {
        "success": False,
        "error": "INVALID_CREDENTIAL_FORMAT",
        "message": "Credential format does not conform to W3C spec",
    }

    with patch("src.credentials.sybol_client.httpx.post", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="422"):
            _client().sign_credential(UNSIGNED_PAYLOAD)


def test_sign_raises_on_success_false_envelope():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.text = ""
    mock_response.json.return_value = {
        "success": False,
        "error": "INVALID_CREDENTIAL_FORMAT",
        "message": "Missing required field",
    }

    with patch("src.credentials.sybol_client.httpx.post", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="Missing required field"):
            _client().sign_credential(UNSIGNED_PAYLOAD)


def test_sign_raises_on_timeout():
    with patch(
        "src.credentials.sybol_client.httpx.post",
        side_effect=httpx.TimeoutException("timed out"),
    ):
        with pytest.raises(SybolSigningError, match="timed out"):
            _client().sign_credential(UNSIGNED_PAYLOAD)


def test_sign_raises_on_transport_error():
    with patch(
        "src.credentials.sybol_client.httpx.post",
        side_effect=httpx.TransportError("connection refused"),
    ):
        with pytest.raises(SybolSigningError, match="transport"):
            _client().sign_credential(UNSIGNED_PAYLOAD)


# --- sign_credential: response validation ---


def test_sign_raises_when_data_missing():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"success": True}

    with patch("src.credentials.sybol_client.httpx.post", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="data"):
            _client().sign_credential(UNSIGNED_PAYLOAD)


def test_sign_raises_when_proof_missing():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "success": True,
        "data": {"id": "urn:uuid:abc"},
    }

    with patch("src.credentials.sybol_client.httpx.post", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="proof"):
            _client().sign_credential(UNSIGNED_PAYLOAD)


def test_sign_raises_on_non_json_response():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.side_effect = ValueError("not JSON")
    mock_response.text = "<html>error</html>"

    with patch("src.credentials.sybol_client.httpx.post", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="non-JSON"):
            _client().sign_credential(UNSIGNED_PAYLOAD)


# --- sign_credential: contract validation ---


def test_sign_raises_when_issuer_mismatch():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "success": True,
        "data": {**SIGNED_VC, "issuer": "did:example:wrong"},
    }

    client = SybolClient(
        api_url=VALID_URL,
        access_token=VALID_ACCESS_TOKEN,
        id_token=VALID_ID_TOKEN,
        expected_issuer_did="did:sybol:tenant123:issuer",
    )

    with patch("src.credentials.sybol_client.httpx.post", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="issuer DID"):
            client.sign_credential(UNSIGNED_PAYLOAD)


def test_sign_raises_when_credential_type_mismatch():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "success": True,
        "data": {**SIGNED_VC, "type": ["VerifiableCredential", "OtherCredential"]},
    }

    client = SybolClient(
        api_url=VALID_URL,
        access_token=VALID_ACCESS_TOKEN,
        id_token=VALID_ID_TOKEN,
        expected_credential_type="MediaComplianceCredential",
    )

    with patch("src.credentials.sybol_client.httpx.post", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="credential type mismatch"):
            client.sign_credential(UNSIGNED_PAYLOAD)


def test_sign_raises_when_schema_mismatch():
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "success": True,
        "data": {
            **SIGNED_VC,
            "credentialSchema": {"id": "did:example:other-schema", "type": "JsonSchema"},
        },
    }

    client = SybolClient(
        api_url=VALID_URL,
        access_token=VALID_ACCESS_TOKEN,
        id_token=VALID_ID_TOKEN,
        expected_schema_id="https://catalog.sybol.id/schemas/MediaComplianceCredential",
    )

    with patch("src.credentials.sybol_client.httpx.post", return_value=mock_response):
        with pytest.raises(SybolSigningError, match="credentialSchema mismatch"):
            client.sign_credential(UNSIGNED_PAYLOAD)