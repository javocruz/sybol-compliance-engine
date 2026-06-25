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
        or "0acdb1ed-4cd2-41a4-917a-b7270d6166b9"
    )
    sybol_issuer_key: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_ISSUER_KEY")
        or "did:web:did.develop.sybol.id:tenants:sybol#ebcbb38c-1cfb-41a9-80a2-17bcaa3a5564"
    )
    sybol_cognito_client_id: str | None = field(
        default_factory=lambda: os.getenv(
            "SYBOL_COGNITO_CLIENT_ID", "39ergo6f0l4gk195ld6sjoi41p"
        )
    )
    sybol_cognito_region: str = field(
        default_factory=lambda: os.getenv("SYBOL_COGNITO_REGION", "eu-west-1")
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


def get_sybol_client(settings: Settings | None = None):
    from src.credentials.sybol_client import SybolClient

    settings = settings or get_settings()
    return SybolClient(
        api_base_url=settings.sybol_api_base_url,
        access_token=settings.sybol_access_token,
        id_token=settings.sybol_id_token,
        email=settings.sybol_email,
        password=settings.sybol_password,
        document_id=settings.sybol_document_id,
        issuer_key=settings.sybol_issuer_key,
        cognito_client_id=settings.sybol_cognito_client_id,
        cognito_region=settings.sybol_cognito_region,
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
