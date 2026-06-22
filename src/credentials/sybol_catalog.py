"""Sybol catalog helpers for Media Compliance credential (develop tenant)."""

from __future__ import annotations

from typing import Any

import httpx

from .sybol_client import SybolClient, SybolSigningError

# Created on develop 2026-06-22 via POST /api/catalog/documents (tenant sybol)
DEFAULT_MEDIA_COMPLIANCE_DOCUMENT_ID = "0acdb1ed-4cd2-41a4-917a-b7270d6166b9"
DEFAULT_MEDIA_COMPLIANCE_CODE = "MEDIA_COMPLIANCE_IE"

MEDIA_CLAIM_KEYS: tuple[str, ...] = (
    "mediaHash",
    "authenticityScore",
    "complianceStatus",
    "modelVersion",
    "scoreBreakdown.m",
    "scoreBreakdown.a",
    "scoreBreakdown.v",
    "scoreBreakdown.p",
    "regulationRefs",
    "ragSummary",
    "evidenceUrl",
)

_CLAIM_LABELS: dict[str, tuple[str, str]] = {
    "mediaHash": ("Media hash", "SHA-256 of image bytes"),
    "authenticityScore": ("Authenticity score", "Combined m/a/v/p score"),
    "complianceStatus": ("Compliance status", "compliant or non-compliant"),
    "modelVersion": ("Model version", "Scoring model identifier"),
    "scoreBreakdown.m": ("Metadata signal", "EXIF / metadata sub-score"),
    "scoreBreakdown.a": ("Artifact signal", "Compression artifact sub-score"),
    "scoreBreakdown.v": ("Vision signal", "Visual anomaly sub-score"),
    "scoreBreakdown.p": ("Provenance signal", "Provenance index sub-score"),
    "regulationRefs": ("Regulation references", "JSON array of applicable articles"),
    "ragSummary": ("Compliance summary", "RAG-generated regulatory summary"),
    "evidenceUrl": ("Evidence URL", "Audit trail pointer in Qdrant"),
}


def find_catalog_document_by_code(
    client: SybolClient, code: str
) -> dict[str, Any] | None:
    for doc in client.list_catalog_documents(search=code):
        if doc.get("code") == code:
            return doc
    return None


def ensure_media_compliance_catalog(
    client: SybolClient,
    *,
    activate: bool = True,
) -> str:
    """
    Return documentId for MEDIA_COMPLIANCE_IE, creating or activating if needed.

    Issuance works with inline claims even before catalog claim rows exist;
    claim rows improve wallet display metadata.
    """
    existing = find_catalog_document_by_code(client, DEFAULT_MEDIA_COMPLIANCE_CODE)
    if existing and existing.get("id"):
        doc_id = str(existing["id"])
        if activate and existing.get("state") != "active":
            client.update_catalog_document(doc_id, {**existing, "state": "active"})
        _ensure_catalog_claim_rows(client, doc_id)
        return doc_id

    created = client.create_catalog_document(
        code=DEFAULT_MEDIA_COMPLIANCE_CODE,
        label="Media Compliance",
        description="IEU Labs image authenticity and EU regulatory compliance VC",
        compliance_path="priv.ie.media",
        supported_formats=["jwt_vc_json"],
    )
    doc_id = str(created["id"])
    if activate:
        client.update_catalog_document(doc_id, {**created, "state": "active"})
    _ensure_catalog_claim_rows(client, doc_id)
    return doc_id


def _ensure_catalog_claim_rows(client: SybolClient, document_id: str) -> None:
    doc = client.get_catalog_document(document_id)
    existing = {
        c.get("key")
        for c in (doc.get("claims") or [])
        if isinstance(c, dict) and c.get("key")
    }
    for key in MEDIA_CLAIM_KEYS:
        if key in existing:
            continue
        label, description = _CLAIM_LABELS.get(key, (key, key))
        try:
            client.create_catalog_claim(
                document_id=document_id,
                key=key,
                label=label,
                description=description,
            )
        except SybolSigningError as exc:
            # Non-fatal — issuance still works with inline claim keys.
            if "already exists" not in str(exc).lower():
                raise
