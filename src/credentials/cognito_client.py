"""AWS Cognito USER_PASSWORD_AUTH via the JSON API (no Sybol /auth/login)."""

from typing import Any

import httpx

COGNITO_TARGET = "AWSCognitoIdentityProviderService.InitiateAuth"
AUTH_FLOW = "USER_PASSWORD_AUTH"


class CognitoAuthError(Exception):
    """Raised when Cognito InitiateAuth fails or returns an unsupported challenge."""


def _cognito_url(region: str) -> str:
    return f"https://cognito-idp.{region}.amazonaws.com/"


def _extract_error_message(payload: object, fallback: str) -> str:
    if isinstance(payload, dict):
        message = payload.get("message")
        if message:
            return str(message)
        err_type = payload.get("__type", "")
        if err_type:
            return str(err_type).rsplit("#", 1)[-1]
    return fallback[:400]


def initiate_password_auth(
    username: str,
    password: str,
    *,
    client_id: str,
    region: str = "eu-west-1",
    timeout: float = 30.0,
) -> dict[str, str]:
    """
    Call Cognito InitiateAuth (USER_PASSWORD_AUTH).

    Returns accessToken, idToken, and optional refreshToken (camelCase keys).
    """
    if not client_id:
        raise CognitoAuthError(
            "SYBOL_COGNITO_CLIENT_ID is not set. Add it to src/.env."
        )

    body = {
        "AuthFlow": AUTH_FLOW,
        "ClientId": client_id,
        "AuthParameters": {
            "USERNAME": username,
            "PASSWORD": password,
        },
    }
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": COGNITO_TARGET,
    }

    try:
        response = httpx.post(
            _cognito_url(region),
            headers=headers,
            json=body,
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise CognitoAuthError(f"Cognito request timed out after {timeout}s") from exc
    except httpx.TransportError as exc:
        raise CognitoAuthError(f"Cognito transport error: {exc}") from exc

    try:
        payload: Any = response.json()
    except Exception as exc:
        raise CognitoAuthError(
            f"Cognito returned non-JSON response: {response.text[:200]}"
        ) from exc

    if not response.is_success:
        raise CognitoAuthError(
            _extract_error_message(payload, response.text or "Cognito auth failed")
        )

    if not isinstance(payload, dict):
        raise CognitoAuthError("Cognito returned an unexpected response.")

    challenge = payload.get("ChallengeName")
    if challenge:
        raise CognitoAuthError(
            f"Cognito requires challenge {challenge!r} — complete it in the Sybol wallet, "
            "then try again."
        )

    auth_result = payload.get("AuthenticationResult")
    if not isinstance(auth_result, dict):
        raise CognitoAuthError("Cognito response missing AuthenticationResult.")

    access = auth_result.get("AccessToken")
    id_token = auth_result.get("IdToken")
    if not access or not id_token:
        raise CognitoAuthError("Cognito response missing AccessToken or IdToken.")

    tokens: dict[str, str] = {
        "accessToken": str(access),
        "idToken": str(id_token),
    }
    refresh = auth_result.get("RefreshToken")
    if refresh:
        tokens["refreshToken"] = str(refresh)
    return tokens
