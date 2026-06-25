import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import Settings, get_settings
from src.api.main import app
from src.api.token_store import create_store
from src.credentials.cognito_client import CognitoAuthError

COGNITO_TOKENS = {
    "accessToken": "session-access-token",
    "idToken": "session-id-token",
    "refreshToken": "session-refresh-token",
}


@pytest.fixture
def client():
    app.state.token_store = create_store()
    return TestClient(app)


@pytest.fixture
def sybol_settings():
    return Settings(
        sybol_document_id="doc-1",
        sybol_issuer_key="issuer-1",
        sybol_recipient_did="did:example:recipient",
        sybol_cognito_client_id="client-id",
        sybol_cognito_region="eu-west-1",
    )


def test_auth_status_unauthenticated(client, monkeypatch):
    monkeypatch.delenv("SYBOL_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("SYBOL_ID_TOKEN", raising=False)
    monkeypatch.delenv("SYBOL_EMAIL", raising=False)
    monkeypatch.delenv("SYBOL_PASSWORD", raising=False)

    response = client.get("/api/auth/status")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is False
    assert body["session_active"] is False


def test_auth_login_stores_session(client, sybol_settings, mocker):
    app.dependency_overrides[get_settings] = lambda: sybol_settings
    mocker.patch(
        "src.api.routes.auth.initiate_password_auth",
        return_value=COGNITO_TOKENS,
    )

    try:
        response = client.post(
            "/api/auth/login",
            json={"email": "user@ie.id", "password": "secret"},
        )
        assert response.status_code == 200
        assert response.json()["authenticated"] is True
        assert response.json()["session_active"] is True
        assert response.json()["email"] == "user@ie.id"

        status = client.get("/api/auth/status")
        assert status.json()["session_active"] is True
        assert status.json()["authenticated"] is True
        assert len(app.state.token_store) == 1
        stored = next(iter(app.state.token_store.values()))
        assert stored.id_token == "session-id-token"
    finally:
        app.dependency_overrides.clear()


def test_auth_login_failure_returns_401(client, sybol_settings, mocker):
    app.dependency_overrides[get_settings] = lambda: sybol_settings
    mocker.patch(
        "src.api.routes.auth.initiate_password_auth",
        side_effect=CognitoAuthError("Incorrect username or password."),
    )

    try:
        response = client.post(
            "/api/auth/login",
            json={"email": "user@ie.id", "password": "wrong"},
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_auth_logout_clears_session(client, sybol_settings, mocker):
    app.dependency_overrides[get_settings] = lambda: sybol_settings
    mocker.patch(
        "src.api.routes.auth.initiate_password_auth",
        return_value=COGNITO_TOKENS,
    )

    try:
        client.post(
            "/api/auth/login",
            json={"email": "user@ie.id", "password": "secret"},
        )
        logout = client.post("/api/auth/logout")
        assert logout.status_code == 200

        status = client.get("/api/auth/status")
        assert status.json()["session_active"] is False
        assert len(app.state.token_store) == 0
    finally:
        app.dependency_overrides.clear()
