from fastapi import APIRouter, Depends, HTTPException
from qdrant_client import QdrantClient

from src.api.dependencies import Settings, get_qdrant_client, get_settings
from src.api.schemas import VerifyResponse
from src.credentials.audit import read_audit_record

router = APIRouter(tags=["credentials"])


def _normalize_vc_id(vc_id: str) -> str:
    return vc_id.removeprefix("urn:uuid:")


@router.get(
    "/verify/{vc_id}",
    response_model=VerifyResponse,
    summary="Verify credential audit record and revocation status",
)
async def verify_credential(
    vc_id: str,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    settings: Settings = Depends(get_settings),
):
    point_id = _normalize_vc_id(vc_id)
    record = read_audit_record(point_id, qdrant_client, settings)
    if not record:
        return VerifyResponse(
            vc_id=vc_id,
            valid=False,
            revoked=False,
            audit_found=False,
            detail="No audit record found for this credential.",
        )

    revoked = bool(record.get("revoked"))
    return VerifyResponse(
        vc_id=vc_id,
        valid=not revoked,
        revoked=revoked,
        audit_found=True,
        detail="Revoked" if revoked else "Audit record present; signature not checked on-chain.",
    )
