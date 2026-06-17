# TODO(Darius): Implement the following fields in the Settings dataclass: sybol_expected_issuer_did, sybol_expected_credential_type, sybol_expected_schema_id

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
    sybol_api_url: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_API_URL")
    )
    sybol_access_token: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_ACCESS_TOKEN")
    )
    sybol_id_token: str | None = field(
        default_factory=lambda: os.getenv("SYBOL_ID_TOKEN")
    )
    sybol_expected_issuer_did: str = field(
        default_factory=lambda: os.getenv(
            "SYBOL_EXPECTED_ISSUER_DID",
            "TBD_pending_issuer_did_confirmation_from_inigo",
        )
    )
    sybol_expected_credential_type: str = field(
        default_factory=lambda: os.getenv(
            "SYBOL_CREDENTIAL_TYPE",
            "MediaComplianceCredential",
        )
    )
    sybol_expected_schema_id: str = field(
        default_factory=lambda: os.getenv(
            "SYBOL_CREDENTIAL_SCHEMA_ID",
            "TBD_pending_catalog_registration_confirmation",
        )
    )
    sybol_request_timeout: float = field(
        default_factory=lambda: float(os.getenv("SYBOL_REQUEST_TIMEOUT", "10.0"))
    )



def get_settings() -> Settings:
    return Settings()


def get_qdrant_client(settings: Settings | None = None) -> QdrantClient:
    settings = settings or get_settings()
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def get_sybol_client(settings: Settings | None = None):
    from src.credentials.sybol_client import SybolClient

    settings = settings or get_settings()
    return SybolClient(
        api_url=settings.sybol_api_url,
        access_token=settings.sybol_access_token,
        id_token=settings.sybol_id_token,
        timeout=settings.sybol_request_timeout,
        # expected_issuer_did=settings.sybol_expected_issuer_did,
        # expected_credential_type=settings.sybol_expected_credential_type,
        # expected_schema_id=settings.sybol_expected_schema_id,
    )


def get_index(request: Request) -> VectorStoreIndex:
    index = getattr(request.app.state, "index", None)
    if index is None:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline not available. Ensure Qdrant is running and the index has been initialized.",
        )
    return index