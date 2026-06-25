import os

from fastapi import Header, HTTPException


def _parse_api_keys() -> set[str]:
    raw = os.getenv("API_KEYS", "")
    return {k.strip() for k in raw.split(",") if k.strip()}


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Optional API key guard for write endpoints. Open when API_KEYS is unset."""
    keys = _parse_api_keys()
    if not keys:
        return
    if not x_api_key or x_api_key not in keys:
        raise HTTPException(401, "Invalid or missing API key")
