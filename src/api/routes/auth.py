from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.dependencies import Settings, get_settings
from src.api.schemas import AuthLoginRequest, AuthLoginResponse, AuthStatusResponse
from src.api.token_store import (
    AuthSession,
    clear_session,
    load_session,
    save_session,
)
from src.credentials.cognito_client import CognitoAuthError, initiate_password_auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_store(request: Request) -> dict:
    store = getattr(request.app.state, "token_store", None)
    if store is None:
        raise HTTPException(503, detail="Auth session store is not initialized.")
    return store


def _session_id(request: Request) -> str | None:
    return request.session.get("auth_sid")


def _catalog_configured(settings: Settings) -> bool:
    return bool(settings.sybol_document_id and settings.sybol_issuer_key)


def _has_env_tokens(settings: Settings) -> bool:
    return bool(settings.sybol_access_token and settings.sybol_id_token)


def _has_env_login(settings: Settings) -> bool:
    return bool(settings.sybol_email and settings.sybol_password)


def _has_active_session(request: Request) -> bool:
    return load_session(_token_store(request), _session_id(request)) is not None


@router.post("/login", response_model=AuthLoginResponse)
async def login(
    body: AuthLoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    try:
        tokens = initiate_password_auth(
            body.email,
            body.password,
            client_id=settings.sybol_cognito_client_id or "",
            region=settings.sybol_cognito_region,
            timeout=settings.sybol_request_timeout,
        )
    except CognitoAuthError as exc:
        raise HTTPException(401, detail=str(exc)) from exc

    store = _token_store(request)
    old_sid = _session_id(request)
    clear_session(store, old_sid)

    sid = save_session(
        store,
        AuthSession(
            access_token=tokens["accessToken"],
            id_token=tokens["idToken"],
            email=body.email,
            refresh_token=tokens.get("refreshToken"),
        ),
    )
    request.session["auth_sid"] = sid

    return AuthLoginResponse(
        authenticated=True,
        email=body.email,
        catalog_configured=_catalog_configured(settings),
        session_active=True,
    )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(
    request: Request,
    settings: Settings = Depends(get_settings),
):
    session = load_session(_token_store(request), _session_id(request))
    authenticated = (
        session is not None
        or _has_env_tokens(settings)
        or _has_env_login(settings)
    )
    email = session.email if session else settings.sybol_email
    return AuthStatusResponse(
        authenticated=authenticated,
        email=email,
        catalog_configured=_catalog_configured(settings),
        session_active=session is not None,
    )


@router.post("/logout", response_model=AuthLoginResponse)
async def logout(request: Request, settings: Settings = Depends(get_settings)):
    clear_session(_token_store(request), _session_id(request))
    request.session.pop("auth_sid", None)
    return AuthLoginResponse(
        authenticated=_has_env_tokens(settings) or _has_env_login(settings),
        email=settings.sybol_email,
        catalog_configured=_catalog_configured(settings),
        session_active=False,
    )
