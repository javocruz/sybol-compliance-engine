from fastapi import APIRouter, Depends, HTTPException, Query
from qdrant_client import QdrantClient

from src.api.dependencies import Settings, get_qdrant_client, get_settings
from src.api.schemas import AuditListResponse, AuditRecordResponse
from src.credentials.audit import get_audit_record, list_audit_records

router = APIRouter(tags=["audit"])


@router.get(
    "/audit",
    response_model=AuditListResponse,
    summary="List metadata-only audit trail records",
    responses={503: {"description": "Qdrant unavailable"}},
)
async def list_records(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    settings: Settings = Depends(get_settings),
):
    try:
        records, total = list_audit_records(
            qdrant_client,
            settings,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        raise HTTPException(
            503,
            detail=f"Audit trail unavailable — Qdrant may be down: {exc}",
        ) from exc

    return AuditListResponse(
        records=[AuditRecordResponse.model_validate(record) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/audit/{record_id}",
    response_model=AuditRecordResponse,
    summary="Get a single audit trail record by credential UUID",
    responses={
        404: {"description": "Audit record not found"},
        503: {"description": "Qdrant unavailable"},
    },
)
async def get_record(
    record_id: str,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    settings: Settings = Depends(get_settings),
):
    try:
        record = get_audit_record(record_id, qdrant_client, settings)
    except Exception as exc:
        raise HTTPException(
            503,
            detail=f"Audit trail unavailable — Qdrant may be down: {exc}",
        ) from exc

    if record is None:
        raise HTTPException(404, "Audit record not found")

    return AuditRecordResponse.model_validate(record)
