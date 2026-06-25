from fastapi import APIRouter, Depends, HTTPException
from qdrant_client import QdrantClient

from src.api.dependencies import Settings, get_qdrant_client, get_settings
from src.credentials.audit import read_audit_record

router = APIRouter(tags=["audit"])


@router.get(
    "/audit/{point_id}",
    summary="Fetch metadata-only audit record for an issued credential",
    responses={404: {"description": "Audit record not found"}},
)
async def get_audit_record(
    point_id: str,
    client: QdrantClient = Depends(get_qdrant_client),
    settings: Settings = Depends(get_settings),
):
    payload = read_audit_record(point_id, client, settings)
    if payload is None:
        raise HTTPException(404, "Audit record not found")
    return payload
