"""
Sybol BusinessWallet API client (OpenAPI v4 — openapi-wallet.yaml).

Authentication: POST /auth/login → accessToken + idToken (Cognito via REST).
Issuance: POST /api/bl/credentials with CredentialIssueRequest (catalog + claims).
"""

import logging
from typing import Any

import httpx

from src.credentials.auth_tokens import is_valid_jwt, normalize_token

logger = logging.getLogger(__name__)

_TBD_PREFIX = "TBD_"
DEFAULT_API_BASE_URL = "https://api.develop.wallet.sybol.id"


class SybolSigningError(Exception):
    """Raised when the Sybol API returns an error or an unexpected response."""


class SybolNotConfiguredError(Exception):
    """Raised when Sybol credentials or catalog config are not set."""


class SybolClient:
    def __init__(
        self,
        api_base_url: str | None,
        access_token: str | None,
        id_token: str | None,
        email: str | None = None,
        password: str | None = None,
        document_id: str | None = None,
        issuer_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_base_url = (api_base_url or DEFAULT_API_BASE_URL).rstrip("/")
        self._access_token = normalize_token(access_token)
        self._id_token = normalize_token(id_token)
        self._email = email
        self._password = password
        self._document_id = document_id
        self._issuer_key = issuer_key
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        """True when base URL, catalog ids, and auth (tokens or email/password) are set."""
        if not self._api_base_url or self._is_placeholder(self._api_base_url):
            return False
        if self._is_placeholder(self._document_id) or not self._document_id:
            return False
        if self._is_placeholder(self._issuer_key) or not self._issuer_key:
            return False
        return self._has_valid_tokens() or self._has_login_credentials()

    def _is_placeholder(self, value: str | None) -> bool:
        return not value or value.startswith(_TBD_PREFIX)

    def _has_valid_tokens(self) -> bool:
        return (
            not self._is_placeholder(self._access_token)
            and not self._is_placeholder(self._id_token)
            and self._access_token is not None
            and self._id_token is not None
        )

    def _has_login_credentials(self) -> bool:
        return (
            not self._is_placeholder(self._email)
            and not self._is_placeholder(self._password)
            and self._email is not None
            and self._password is not None
        )

    def _headers(self) -> dict[str, str]:
        if not self._has_valid_tokens():
            raise SybolNotConfiguredError(
                "Sybol tokens missing. Set SYBOL_ACCESS_TOKEN and SYBOL_ID_TOKEN, "
                "or SYBOL_EMAIL and SYBOL_PASSWORD for /auth/login."
            )
        assert self._access_token is not None
        assert self._id_token is not None
        if not is_valid_jwt(self._id_token):
            raise SybolSigningError(
                "Invalid Sybol ID token — expected a 3-part JWT. Sign in again on the Issue tab."
            )
        return {
            "Authorization": f"Bearer {self._access_token}",
            "x-id-token": self._id_token,
            "Content-Type": "application/json",
        }

    def login(self) -> dict[str, Any]:
        """POST /auth/login — exchange email/password for Cognito token set."""
        if not self._has_login_credentials():
            raise SybolNotConfiguredError(
                "Set SYBOL_EMAIL and SYBOL_PASSWORD to use /auth/login."
            )
        assert self._email is not None
        assert self._password is not None

        try:
            response = httpx.post(
                f"{self._api_base_url}/auth/login",
                json={"email": self._email, "password": self._password},
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise SybolSigningError(
                f"Sybol login timed out after {self._timeout}s"
            ) from exc
        except httpx.TransportError as exc:
            raise SybolSigningError(f"Sybol login transport error: {exc}") from exc

        envelope = _parse_json(response)
        if not response.is_success:
            raise SybolSigningError(
                f"Sybol login failed ({response.status_code}): "
                f"{_extract_error_message(envelope, response.text)}"
            )

        if isinstance(envelope, dict) and envelope.get("success") is False:
            challenge = envelope.get("challengeName")
            if challenge:
                raise SybolSigningError(
                    f"Sybol login requires challenge {challenge!r} — complete MFA in wallet UI."
                )
            raise SybolSigningError(
                f"Sybol login failed: {_extract_error_message(envelope, response.text)}"
            )

        data = envelope.get("data") if isinstance(envelope, dict) else None
        if not isinstance(data, dict):
            raise SybolSigningError("Sybol login response missing data envelope.")

        access = data.get("accessToken")
        id_token = data.get("idToken")
        if not access or not id_token:
            raise SybolSigningError("Sybol login response missing accessToken or idToken.")

        self._access_token = access
        self._id_token = id_token
        return data

    def ensure_authenticated(self) -> None:
        if not self._has_valid_tokens():
            self.login()

    def list_catalog_documents(self, search: str | None = None) -> list[dict[str, Any]]:
        """GET /api/catalog/documents — discover documentId for issuance."""
        self.ensure_authenticated()
        params: dict[str, str] = {}
        if search:
            params["search"] = search
        envelope = self._request("GET", "/api/catalog/documents", params=params or None)
        data = envelope.get("data")
        if isinstance(data, list):
            return data
        return []

    def issue_credential(self, issue_request: dict[str, Any]) -> dict[str, Any]:
        """
        POST /api/bl/credentials — catalog-based issuance (OpenAPI CredentialIssueRequest).
        Returns the credential object from the response data envelope.
        """
        self.ensure_authenticated()
        envelope = self._request("POST", "/api/bl/credentials", json=issue_request)
        data = envelope.get("data")
        if not isinstance(data, dict):
            raise SybolSigningError(
                "Sybol issue response missing 'data' field — possible schema mismatch."
            )
        if not _credential_is_signed(data):
            raise SybolSigningError(
                "Sybol issue response missing signed credential "
                "(expected signed_token or proof)."
            )
        return data

    def sign_credential(self, issue_request: dict[str, Any]) -> dict[str, Any]:
        """Alias for issue_credential — same catalog issuance flow."""
        return self.issue_credential(issue_request)

    def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        url = f"{self._api_base_url}{path}"
        try:
            response = httpx.request(
                method,
                url,
                headers=self._headers(),
                json=json,
                params=params,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise SybolSigningError(
                f"Sybol API request timed out after {self._timeout}s"
            ) from exc
        except httpx.TransportError as exc:
            raise SybolSigningError(f"Sybol API transport error: {exc}") from exc

        envelope = _parse_json(response)
        if not response.is_success:
            message = _extract_error_message(envelope, response.text)
            logger.error(
                "Sybol API error: %s %s status=%s body=%s",
                method,
                path,
                response.status_code,
                response.text[:500],
            )
            raise SybolSigningError(
                f"Sybol API returned {response.status_code}: {message}"
            )

        if not isinstance(envelope, dict):
            raise SybolSigningError(
                f"Sybol API returned unexpected type: {type(envelope).__name__}"
            )

        if envelope.get("success") is False:
            raise SybolSigningError(
                f"Sybol API error: {_extract_error_message(envelope, response.text)}"
            )

        return envelope


def _parse_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception as exc:
        raise SybolSigningError(
            f"Sybol API returned non-JSON response: {response.text[:200]}"
        ) from exc


def _credential_is_signed(data: dict[str, Any]) -> bool:
    if data.get("signed_token"):
        return True
    if isinstance(data.get("proof"), dict):
        return True
    if isinstance(data.get("signedToken"), str):
        return True
    return False


def _extract_error_message(envelope: object, fallback_text: str) -> str:
    if isinstance(envelope, dict):
        for key in ("message", "error"):
            value = envelope.get(key)
            if value:
                return str(value)[:400]
    return fallback_text[:400]
