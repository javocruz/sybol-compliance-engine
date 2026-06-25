import os
from dataclasses import dataclass, field

from fastapi import HTTPException, Request
from llama_index.core import VectorStoreIndex
from qdrant_client import QdrantClient

@dataclass
class Settings:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "dev"))
    qdrant_url: str = field(
        default_factory=lambda: os.getenv("QDRANT_URL", "http://localhost:6333")
    )
    qdrant_api_key: str | None = field(
        default_factory=lambda: os.getenv("QDRANT_API_KEY")
    )
    qdrant_collection: str = field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION", "regulations")
    )
    qdrant_audit_collection: str = field(
        default_factory=lambda: os.getenv("QDRANT_AUDIT_COLLECTION", "media_audit")
    )
    # Sybol BusinessWallet API (OpenAPI v4)
    sybol_api_base_url: str = field(
        default_factory=lambda: os.getenv(
            "SYBOL_API_BASE_URL", "https://api.develop.wallet.sybol.id"
        )
    )
    sybol_access_token: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_ACCESS_TOKEN")
    )
    sybol_id_token: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_ID_TOKEN")
    )
    sybol_email: str | None = field(default_factory=lambda: os.getenv("SYBOL_EMAIL"))
    sybol_password: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_PASSWORD")
    )
    sybol_document_id: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_DOCUMENT_ID")
    )
    sybol_issuer_key: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_ISSUER_KEY")
    )
    sybol_subject_did: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_SUBJECT_DID")
    )
    sybol_recipient_did: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_RECIPIENT_DID")
    )
    sybol_credential_format: str = field(
        default_factory=lambda: os.getenv("SYBOL_CREDENTIAL_FORMAT", "jwt_vc_json")
    )
    sybol_level_of_assurance: int | None = field(
        default_factory=lambda: _optional_int(os.getenv("SYBOL_LEVEL_OF_ASSURANCE"))
    )
    sybol_request_timeout: float = field(
        default_factory=lambda: float(os.getenv("SYBOL_REQUEST_TIMEOUT", "30.0"))
    )
    sybol_cognito_client_id: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_COGNITO_CLIENT_ID")
        or os.getenv("COGNITO_CLIENT_ID")
    )
    sybol_cognito_region: str = field(
        default_factory=lambda: os.getenv("SYBOL_COGNITO_REGION")
        or os.getenv("COGNITO_REGION", "eu-west-1")
    )
    default_llm_provider: str = field(
        default_factory=lambda: os.getenv("DEFAULT_LLM_PROVIDER", "mistral")
    )
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    )


def _optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value)


def get_settings() -> Settings:
    return Settings()


def get_qdrant_client(settings: Settings | None = None) -> QdrantClient:
    settings = settings or get_settings()
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def get_sybol_client(request: Request, settings: Settings | None = None):
    from src.api.token_store import load_session
    from src.credentials.auth_tokens import normalize_token
    from src.credentials.sybol_client import SybolClient

    settings = settings or get_settings()
    store = getattr(request.app.state, "token_store", {})
    auth_sid = request.session.get("auth_sid")
    session = load_session(store, auth_sid)

    if auth_sid and session is None:
        raise HTTPException(
            status_code=401,
            detail=(
                "Sign-in session expired (for example after an API restart). "
                "Sign in again on the Issue tab."
            ),
        )

    if session:
        access_token = session.access_token
        id_token = session.id_token
        email = None
        password = None
    else:
        access_token = normalize_token(settings.sybol_access_token)
        id_token = normalize_token(settings.sybol_id_token)
        email = settings.sybol_email
        password = settings.sybol_password

    return SybolClient(
        api_base_url=settings.sybol_api_base_url,
        access_token=access_token,
        id_token=id_token,
        email=email,
        password=password,
        document_id=settings.sybol_document_id,
        issuer_key=settings.sybol_issuer_key,
        timeout=settings.sybol_request_timeout,
    )


def get_index(request: Request) -> VectorStoreIndex:
    index = getattr(request.app.state, "index", None)
    if index is None:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline not available. Ensure Qdrant is running and the index has been initialized.",
        )
    return index
