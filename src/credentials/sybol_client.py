"""
Sybol businessLogic API client for signing Verifiable Credentials.

Endpoint: POST /api/bl/credentials (see sybol_docs/services/businessLogic/api/)
Auth: Authorization Bearer access token + x-id-token (Cognito, tenant-scoped).
Response: { "success": true, "data": { ...signed VC with proof... } }
"""

import logging

import httpx

logger = logging.getLogger(__name__)

_TBD_PREFIX = "TBD_"
DEFAULT_API_URL = "https://api.sybol.io/api/bl/credentials"


class SybolSigningError(Exception):
    """Raised when the Sybol API returns an error or an unexpected response."""


class SybolNotConfiguredError(Exception):
    """Raised when Sybol signing credentials/endpoint are not yet configured."""


class SybolClient:
    def __init__(
        self,
        api_url: str | None,
        access_token: str | None,
        id_token: str | None,
        timeout: float = 10.0,
        expected_issuer_did: str | None = None,
        expected_credential_type: str | None = None,
        expected_schema_id: str | None = None,
    ) -> None:
        self._api_url = api_url
        self._access_token = access_token
        self._id_token = id_token
        self._timeout = timeout
        self._expected_issuer_did = _normalize_expected(expected_issuer_did)
        self._expected_credential_type = _normalize_expected(expected_credential_type)
        self._expected_schema_id = _normalize_expected(expected_schema_id)

    @property
    def is_configured(self) -> bool:
        """True only when endpoint and both Cognito tokens are present and not placeholders."""
        for value in (self._api_url, self._access_token, self._id_token):
            if not value or value.startswith(_TBD_PREFIX):
                return False
        return True

    def sign_credential(self, payload: dict) -> dict:
        """
        Submit an unsigned VC payload to the Sybol businessLogic API.
        Returns the signed VC dict from the response data envelope (must contain 'proof').

        Raises:
            SybolNotConfiguredError: endpoint/credentials not configured.
            SybolSigningError: signing request failed or response was invalid.
        """
        if not self.is_configured:
            raise SybolNotConfiguredError(
                "Sybol signing is not configured. Set SYBOL_API_URL, "
                "SYBOL_ACCESS_TOKEN, and SYBOL_ID_TOKEN."
            )

        assert self._api_url is not None
        assert self._access_token is not None
        assert self._id_token is not None

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "x-id-token": self._id_token,
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                self._api_url, json=payload, headers=headers, timeout=self._timeout
            )
        except httpx.TimeoutException as exc:
            raise SybolSigningError(
                f"Sybol API request timed out after {self._timeout}s"
            ) from exc
        except httpx.TransportError as exc:
            raise SybolSigningError(f"Sybol API transport error: {exc}") from exc

        try:
            envelope = response.json()
        except Exception as exc:
            raise SybolSigningError(
                f"Sybol API returned non-JSON response: {response.text[:200]}"
            ) from exc

        if not response.is_success:
            message = _extract_error_message(envelope, response.text)
            logger.error(
                "Sybol signing failed: status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise SybolSigningError(
                f"Sybol API returned {response.status_code}: {message}"
            )

        if not isinstance(envelope, dict):
            raise SybolSigningError(
                f"Sybol API returned unexpected response type: {type(envelope).__name__}"
            )

        if envelope.get("success") is False:
            message = _extract_error_message(envelope, response.text)
            logger.error("Sybol signing failed: success=false body=%s", envelope)
            raise SybolSigningError(f"Sybol API error: {message}")

        data = envelope.get("data")
        if not isinstance(data, dict):
            logger.error("Sybol response missing 'data' field: %s", envelope)
            raise SybolSigningError(
                "Sybol API response is missing required 'data' field — "
                "possible schema mismatch."
            )

        if "proof" not in data:
            logger.error("Sybol response data missing 'proof' field: %s", data)
            raise SybolSigningError(
                "Sybol API response data is missing required 'proof' field — "
                "possible schema mismatch."
            )

        _validate_expected_contract(
            data,
            expected_issuer_did=self._expected_issuer_did,
            expected_credential_type=self._expected_credential_type,
            expected_schema_id=self._expected_schema_id,
        )

        return data


def _extract_error_message(envelope: object, fallback_text: str) -> str:
    if isinstance(envelope, dict):
        for key in ("message", "error"):
            value = envelope.get(key)
            if value:
                return str(value)[:400]
    return fallback_text[:400]


def _normalize_expected(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(_TBD_PREFIX):
        return None
    return value


def _validate_expected_contract(
    data: dict,
    *,
    expected_issuer_did: str | None,
    expected_credential_type: str | None,
    expected_schema_id: str | None,
) -> None:
    if expected_issuer_did and data.get("issuer") != expected_issuer_did:
        logger.error(
            "Sybol response issuer mismatch: expected=%s actual=%s data=%s",
            expected_issuer_did,
            data.get("issuer"),
            data,
        )
        raise SybolSigningError(
            f"Sybol API returned unexpected issuer DID: expected {expected_issuer_did}, "
            f"got {data.get('issuer')}"
        )

    if expected_credential_type:
        types = data.get("type")
        if isinstance(types, str):
            types = [types]
        if not isinstance(types, list) or expected_credential_type not in types:
            logger.error(
                "Sybol response type mismatch: expected=%s actual=%s data=%s",
                expected_credential_type,
                data.get("type"),
                data,
            )
            raise SybolSigningError(
                "Sybol API returned credential type mismatch — "
                f"expected {expected_credential_type}"
            )

    if expected_schema_id:
        credential_schema = data.get("credentialSchema")
        schema_id = None
        if isinstance(credential_schema, dict):
            schema_id = credential_schema.get("id")
        elif isinstance(credential_schema, str):
            schema_id = credential_schema

        if schema_id != expected_schema_id:
            logger.error(
                "Sybol response schema mismatch: expected=%s actual=%s data=%s",
                expected_schema_id,
                schema_id,
                data,
            )
            raise SybolSigningError(
                "Sybol API returned credentialSchema mismatch — "
                f"expected {expected_schema_id}"
            )