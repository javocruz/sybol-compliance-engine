"""AWS Cognito USER_PASSWORD_AUTH for Sybol develop (no /auth/* API wrapper)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_COGNITO_REGION = "eu-west-1"
DEFAULT_COGNITO_USER_POOL_ID = "eu-west-1_Lpg65AWPJ"
DEFAULT_COGNITO_CLIENT_ID = "39ergo6f0l4gk195ld6sjoi41p"

_COGNITO_TARGET = "AWSCognitoIdentityProviderService.InitiateAuth"


class CognitoAuthError(Exception):
    """Cognito InitiateAuth failed."""


def cognito_user_password_login(
    email: str,
    password: str,
    *,
    client_id: str = DEFAULT_COGNITO_CLIENT_ID,
    region: str = DEFAULT_COGNITO_REGION,
    timeout: float = 30.0,
) -> dict[str, str]:
    """
    Return accessToken, idToken, refreshToken via Cognito USER_PASSWORD_AUTH.

    Maps Cognito AuthenticationResult to Sybol token field names.
    """
    url = f"https://cognito-idp.{region}.amazonaws.com/"
    payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": client_id,
        "AuthParameters": {
            "USERNAME": email,
            "PASSWORD": password,
        },
    }
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": _COGNITO_TARGET,
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    except httpx.TimeoutException as exc:
        raise CognitoAuthError(f"Cognito login timed out after {timeout}s") from exc
    except httpx.TransportError as exc:
        raise CognitoAuthError(f"Cognito transport error: {exc}") from exc

    body: Any
    try:
        body = response.json()
    except Exception as exc:
        raise CognitoAuthError(
            f"Cognito returned non-JSON ({response.status_code}): {response.text[:200]}"
        ) from exc

    if response.status_code != 200:
        message = body.get("message") or body.get("__type") or response.text[:300]
        raise CognitoAuthError(f"Cognito error ({response.status_code}): {message}")

    if "ChallengeName" in body:
        challenge = body["ChallengeName"]
        raise CognitoAuthError(
            f"Cognito login requires challenge {challenge!r} (e.g. MFA or password reset)."
        )

    result = body.get("AuthenticationResult")
    if not isinstance(result, dict):
        raise CognitoAuthError("Cognito response missing AuthenticationResult.")

    access = result.get("AccessToken")
    id_token = result.get("IdToken")
    if not access or not id_token:
        raise CognitoAuthError("Cognito AuthenticationResult missing AccessToken or IdToken.")

    tokens = {
        "accessToken": access,
        "idToken": id_token,
    }
    refresh = result.get("RefreshToken")
    if refresh:
        tokens["refreshToken"] = refresh
    return tokens
