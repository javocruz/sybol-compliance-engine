"""Helpers for Cognito JWT tokens used with the Sybol API."""


def normalize_token(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def is_valid_jwt(token: str | None) -> bool:
    normalized = normalize_token(token)
    if not normalized:
        return False
    parts = normalized.split(".")
    return len(parts) == 3 and all(parts)
