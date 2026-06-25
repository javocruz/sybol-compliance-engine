import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from llama_index.core import VectorStoreIndex
from qdrant_client import QdrantClient

from src.api.dependencies import (
    Settings,
    get_index,
    get_qdrant_client,
    get_settings,
    get_sybol_client,
)
from src.api.schemas import IssueResponse
from src.credentials.audit import write_audit_record
from src.credentials.catalog_issue_builder import build_catalog_issue_request
from src.credentials.sybol_client import (
    SybolClient,
    SybolSigningError,
)
from src.credentials.vc_builder import build_vc_payload
from src.rag.llm import normalize_provider
from src.rag.query import query_regulations
from src.scoring.pipeline import score_image
from src.scoring.preprocess import ScoringError

router = APIRouter(tags=["credentials"])

SUPPORTED_TYPES = ("image/jpeg", "image/png", "image/webp")


@router.post(
    "/issue",
    response_model=IssueResponse,
    summary="Issue a signed W3C Verifiable Credential for a media file",
    responses={
        400: {"description": "Unsupported or corrupted file"},
        502: {"description": "Sybol signing API returned an error"},
        503: {"description": "Sybol signing not configured, or Qdrant unavailable"},
    },
)
async def issue(
    file: UploadFile = File(...),
    index: VectorStoreIndex = Depends(get_index),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    settings: Settings = Depends(get_settings),
    sybol: SybolClient = Depends(get_sybol_client),
):
    if file.content_type not in SUPPORTED_TYPES:
        raise HTTPException(400, "Unsupported file type")

    content = await file.read()
    try:
        result = score_image(
            content,
            filename=file.filename,
            content_type=file.content_type,
        )
    except ScoringError as exc:
        raise HTTPException(400, detail=str(exc)) from exc

    rag_query = (
        f"What EU regulations apply to media with authenticity score "
        f"{result.authenticity_score:.2f} and compliance status "
        f"{result.compliance_status.value}?"
    )
    try:
        rag = query_regulations(
            rag_query,
            index,
            llm_provider=normalize_provider(settings.default_llm_provider),
        )
    except Exception as exc:
        raise HTTPException(
            503,
            detail=f"RAG pipeline failed — LLM or Qdrant may be unavailable: {exc}",
        ) from exc

    credential_id = f"urn:uuid:{uuid.uuid4()}"

    try:
        evidence_url = write_audit_record(
            result, rag, credential_id, qdrant_client, settings
        )
    except Exception as exc:
        raise HTTPException(
            503,
            detail=f"Audit trail write failed — Qdrant may be unavailable: {exc}",
        ) from exc

    payload = build_vc_payload(
        result, rag, credential_id=credential_id, evidence_url=evidence_url
    )

    if not sybol.is_configured:
        raise HTTPException(
            503,
            detail=(
                "Sybol signing is not configured — sign in on the Issue tab, or set "
                "SYBOL_ACCESS_TOKEN and SYBOL_ID_TOKEN in src/.env. Catalog issuance "
                "also requires SYBOL_DOCUMENT_ID, SYBOL_ISSUER_KEY, and "
                "SYBOL_RECIPIENT_DID."
            ),
        )

    try:
        issue_request = build_catalog_issue_request(
            result, rag, settings=settings, evidence_url=evidence_url
        )
        signed_vc = sybol.issue_credential(issue_request)
    except SybolSigningError as exc:
        raise HTTPException(502, detail=str(exc)) from exc

    return IssueResponse(
        status="signed_vc_issued",
        vc_id=payload["id"],
        detail="Signed VC issued by Sybol",
        signed=True,
        vc_payload=payload,
        signed_vc=signed_vc,
    )
