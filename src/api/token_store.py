"""In-memory auth sessions — Cognito JWTs are too large for signed session cookies."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

SESSION_COOKIE = "sybol_auth_sid"


@dataclass
class AuthSession:
    access_token: str
    id_token: str
    email: str
    refresh_token: str | None = None


def create_store() -> dict[str, AuthSession]:
    return {}


def save_session(store: dict[str, AuthSession], session: AuthSession) -> str:
    session_id = secrets.token_urlsafe(32)
    store[session_id] = session
    return session_id


def load_session(store: dict[str, Any], session_id: str | None) -> AuthSession | None:
    if not session_id or not isinstance(store, dict):
        return None
    entry = store.get(session_id)
    return entry if isinstance(entry, AuthSession) else None


def clear_session(store: dict[str, AuthSession], session_id: str | None) -> None:
    if session_id:
        store.pop(session_id, None)
