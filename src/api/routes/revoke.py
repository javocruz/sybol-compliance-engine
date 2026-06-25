from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import require_api_key
from src.api.dependencies import Settings, get_qdrant_client, get_settings
from src.api.schemas import RevokeResponse
from src.credentials.audit import revoke_audit_record
from qdrant_client import QdrantClient

router = APIRouter(tags=["credentials"])


def _normalize_vc_id(vc_id: str) -> str:
    return vc_id.removeprefix("urn:uuid:")


@router.post(
    "/revoke/{vc_id}",
    response_model=RevokeResponse,
    summary="Revoke a credential (audit trail flag)",
)
async def revoke_credential(
    vc_id: str,
    _: None = Depends(require_api_key),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    settings: Settings = Depends(get_settings),
):
    point_id = _normalize_vc_id(vc_id)
    ok = revoke_audit_record(point_id, qdrant_client, settings)
    if not ok:
        raise HTTPException(404, "Audit record not found for this credential.")
    return RevokeResponse(
        vc_id=vc_id,
        revoked=True,
        detail="Credential marked revoked in audit store.",
    )
