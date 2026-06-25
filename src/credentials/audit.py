from datetime import datetime, timezone

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.api.dependencies import Settings
from src.rag.models import ComplianceResult
from src.scoring.models import ScoringResult


def build_evidence_url(point_id: str, settings: Settings) -> str:
    """Public audit URL when PUBLIC_BASE_URL is set; else raw Qdrant point URL."""
    public = (settings.public_base_url or "").rstrip("/")
    if public:
        return f"{public}/api/audit/{point_id}"
    collection = settings.qdrant_audit_collection
    return f"{settings.qdrant_url}/collections/{collection}/points/{point_id}"


def _ensure_collection(client: QdrantClient, collection_name: str) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )


def write_audit_record(
    result: ScoringResult,
    rag: ComplianceResult,
    credential_id: str,
    client: QdrantClient,
    settings: Settings,
) -> str:
    """
    Write a metadata-only audit record to the Qdrant media_audit collection.
    No raw image bytes are stored (GDPR data minimisation).
    Returns a URL that can be set as evidenceUrl in the VC payload.
    """
    collection = settings.qdrant_audit_collection
    _ensure_collection(client, collection)

    point_id = credential_id.removeprefix("urn:uuid:")

    payload = {
        "mediaHash": result.media_hash,
        "authenticityScore": result.authenticity_score,
        "scoreBreakdown": {
            "m": result.score_breakdown.m,
            "a": result.score_breakdown.a,
            "v": result.score_breakdown.v,
            "p": result.score_breakdown.p,
        },
        "complianceStatus": result.compliance_status.value,
        "modelVersion": result.model_version,
        "analysisTimestamp": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "regulationRefs": [
            {"regulation": r.regulation, "article": r.article, "url": r.source_url}
            for r in rag.regulation_refs
        ],
    }

    client.upsert(
        collection_name=collection,
        points=[PointStruct(id=point_id, vector=[0.0], payload=payload)],
    )

    return build_evidence_url(point_id, settings)


def read_audit_record(
    point_id: str,
    client: QdrantClient,
    settings: Settings,
) -> dict | None:
    """Return audit payload for a credential point id, or None if missing."""
    collection = settings.qdrant_audit_collection
    try:
        points = client.retrieve(collection_name=collection, ids=[point_id])
    except Exception:
        return None
    if not points:
        return None
    payload = points[0].payload
    return dict(payload) if payload else None
