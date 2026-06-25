from datetime import datetime, timezone

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.api.dependencies import Settings
from src.rag.models import ComplianceResult
from src.scoring.models import ScoringResult


def _ensure_collection(client: QdrantClient, collection_name: str) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )


def _collection_exists(client: QdrantClient, collection_name: str) -> bool:
    existing = {c.name for c in client.get_collections().collections}
    return collection_name in existing


def _format_audit_record(point_id: str, payload: dict, settings: Settings) -> dict:
    collection = settings.qdrant_audit_collection
    breakdown = payload.get("scoreBreakdown") or {}
    refs = payload.get("regulationRefs") or []
    return {
        "id": str(point_id),
        "credential_id": f"urn:uuid:{point_id}",
        "evidence_url": (
            f"{settings.qdrant_url}/collections/{collection}/points/{point_id}"
        ),
        "media_hash": payload.get("mediaHash", ""),
        "authenticity_score": payload.get("authenticityScore", 0.0),
        "score_breakdown": {
            "m": breakdown.get("m", 0.0),
            "a": breakdown.get("a", 0.0),
            "v": breakdown.get("v", 0.0),
            "p": breakdown.get("p", 0.0),
        },
        "compliance_status": payload.get("complianceStatus", "review"),
        "model_version": payload.get("modelVersion", ""),
        "analysis_timestamp": payload.get("analysisTimestamp", ""),
        "regulation_refs": [
            {
                "regulation": ref.get("regulation", ""),
                "article": ref.get("article", ""),
                "url": ref.get("url", ""),
            }
            for ref in refs
        ],
    }


def list_audit_records(
    client: QdrantClient,
    settings: Settings,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return audit records newest-first with total count."""
    collection = settings.qdrant_audit_collection
    if not _collection_exists(client, collection):
        return [], 0

    records: list[dict] = []
    next_offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=collection,
            limit=100,
            offset=next_offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            if point.payload:
                records.append(
                    _format_audit_record(str(point.id), point.payload, settings)
                )
        if next_offset is None:
            break

    records.sort(key=lambda record: record["analysis_timestamp"], reverse=True)
    total = len(records)
    return records[offset : offset + limit], total


def get_audit_record(
    record_id: str,
    client: QdrantClient,
    settings: Settings,
) -> dict | None:
    collection = settings.qdrant_audit_collection
    if not _collection_exists(client, collection):
        return None

    points = client.retrieve(
        collection_name=collection,
        ids=[record_id],
        with_payload=True,
        with_vectors=False,
    )
    if not points or not points[0].payload:
        return None

    return _format_audit_record(str(points[0].id), points[0].payload, settings)


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

    return f"{settings.qdrant_url}/collections/{collection}/points/{point_id}"
