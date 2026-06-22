"""AWS Cognito USER_PASSWORD_AUTH for Sybol develop (no /auth/* API wrapper)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_COGNITO_REGION = "eu-west-1"
DEFAULT_COGNITO_USER_POOL_ID = "eu-west-1_Lpg65AWPJ"
DEFAULT_COGNITO_CLIENT_ID = "39ergo6f0l4gk195ld6sjoi41p"
DEFAULT_SYBOL_ROLE = "admin"

_COGNITO_TARGET_LOGIN = "AWSCognitoIdentityProviderService.InitiateAuth"
_COGNITO_TARGET_GET_USER = "AWSCognitoIdentityProviderService.GetUser"
_COGNITO_TARGET_UPDATE_ATTRS = "AWSCognitoIdentityProviderService.UpdateUserAttributes"
_COGNITO_TARGET_DELETE_ATTRS = "AWSCognitoIdentityProviderService.DeleteUserAttributes"


class CognitoAuthError(Exception):
    """Cognito InitiateAuth failed."""


def _cognito_post(
    target: str,
    payload: dict[str, Any],
    *,
    region: str = DEFAULT_COGNITO_REGION,
    timeout: float = 30.0,
) -> dict[str, Any]:
    url = f"https://cognito-idp.{region}.amazonaws.com/"
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": target,
    }
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    except httpx.TimeoutException as exc:
        raise CognitoAuthError(f"Cognito request timed out after {timeout}s") from exc
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
    return body if isinstance(body, dict) else {}


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
    body = _cognito_post(
        _COGNITO_TARGET_LOGIN,
        {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": client_id,
            "AuthParameters": {
                "USERNAME": email,
                "PASSWORD": password,
            },
        },
        region=region,
        timeout=timeout,
    )

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


def get_cognito_user_attributes(
    access_token: str,
    *,
    region: str = DEFAULT_COGNITO_REGION,
    timeout: float = 30.0,
) -> dict[str, str]:
    body = _cognito_post(
        _COGNITO_TARGET_GET_USER,
        {"AccessToken": access_token},
        region=region,
        timeout=timeout,
    )
    attrs = body.get("UserAttributes") or []
    return {
        item["Name"]: item["Value"]
        for item in attrs
        if isinstance(item, dict) and "Name" in item and "Value" in item
    }


def _role_arn_is_malformed(value: str | None) -> bool:
    if not value:
        return False
    if value.startswith("arn:aws:iam::"):
        return False
    return len(value) < 20


def ensure_sybol_role_claims(
    access_token: str,
    *,
    role: str = DEFAULT_SYBOL_ROLE,
    region: str = DEFAULT_COGNITO_REGION,
    timeout: float = 30.0,
) -> bool:
    """
  Fix Cognito attrs so Sybol BL APIs accept the Id token.

  Develop users may have custom:role_arn='admin' without custom:role, which
  breaks STS. Sets custom:role and removes a malformed custom:role_arn.

  Returns True when attributes were changed (caller should re-login for fresh JWT).
    """
    attrs = get_cognito_user_attributes(access_token, region=region, timeout=timeout)
    current_role = attrs.get("custom:role")
    role_arn = attrs.get("custom:role_arn")
    needs_role = current_role != role
    needs_delete_arn = _role_arn_is_malformed(role_arn)

    if not needs_role and not needs_delete_arn:
        return False

    if needs_role:
        _cognito_post(
            _COGNITO_TARGET_UPDATE_ATTRS,
            {
                "AccessToken": access_token,
                "UserAttributes": [{"Name": "custom:role", "Value": role}],
            },
            region=region,
            timeout=timeout,
        )
        logger.info("Set Cognito custom:role=%r for Sybol BL API access.", role)

    if needs_delete_arn:
        _cognito_post(
            _COGNITO_TARGET_DELETE_ATTRS,
            {
                "AccessToken": access_token,
                "UserAttributeNames": ["custom:role_arn"],
            },
            region=region,
            timeout=timeout,
        )
        logger.info("Removed malformed Cognito custom:role_arn for Sybol BL API access.")

    return True
