"""Build Sybol BusinessWallet credential issue body (live develop API)."""

from __future__ import annotations

import json
from typing import Any

from src.api.dependencies import Settings
from src.rag.models import ComplianceResult
from src.scoring.models import ScoringResult

DEFAULT_TENANT_DID = "did:web:did.develop.sybol.id:tenants:sybol"
DEFAULT_CREDENTIAL_FORMAT = "jwt_vc_json"


def _claim_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def build_media_claims(result: ScoringResult, rag: ComplianceResult, *, evidence_url: str | None) -> dict[str, str]:
    claims: dict[str, str] = {
        "mediaHash": result.media_hash,
        "authenticityScore": _claim_value(result.authenticity_score),
        "complianceStatus": result.compliance_status.value,
        "modelVersion": result.model_version,
        "scoreBreakdown.m": _claim_value(result.score_breakdown.m),
        "scoreBreakdown.a": _claim_value(result.score_breakdown.a),
        "scoreBreakdown.v": _claim_value(result.score_breakdown.v),
        "scoreBreakdown.p": _claim_value(result.score_breakdown.p),
        "regulationRefs": _claim_value(
            [
                {
                    "regulation": ref.regulation,
                    "article": ref.article,
                    "url": ref.source_url,
                }
                for ref in rag.regulation_refs
            ]
        ),
        "ragSummary": rag.summary,
    }
    if evidence_url:
        claims["evidenceUrl"] = evidence_url
    return claims


def filter_claims_for_catalog(
    claims: dict[str, str],
    catalog_claim_keys: list[str] | None,
) -> dict[str, str]:
    """Keep only keys defined on the catalog document (plus compliance payload blob)."""
    if not catalog_claim_keys:
        return claims

    allowed = set(catalog_claim_keys)
    filtered = {k: v for k, v in claims.items() if k in allowed}
    if not filtered and claims:
        # Demo fallback: map mediaHash into first catalog key when schemas differ.
        first_key = catalog_claim_keys[0]
        filtered[first_key] = claims.get("mediaHash", "")[:64]
    return filtered


def extract_catalog_claim_keys(catalog_document: dict[str, Any]) -> list[str]:
    raw = catalog_document.get("claims") or []
    keys: list[str] = []
    for item in raw:
        if isinstance(item, dict) and item.get("key"):
            keys.append(str(item["key"]))
    return keys


def build_catalog_issue_request(
    result: ScoringResult,
    rag: ComplianceResult,
    *,
    settings: Settings,
    evidence_url: str | None = None,
    catalog_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Map scoring + RAG output to POST /api/bl/credentials (live develop API).

    Live API expects recipientDid, object-shaped claims, and format jwt_vc_json
    (OpenAPI v4 in repo is partially stale).
    """
    document_id = settings.sybol_document_id
    issuer_key = settings.sybol_issuer_key
    if not document_id or not issuer_key:
        raise ValueError(
            "SYBOL_DOCUMENT_ID and SYBOL_ISSUER_KEY are required for catalog issuance."
        )

    recipient_did = (
        settings.sybol_recipient_did
        or settings.sybol_subject_did
        or DEFAULT_TENANT_DID
    )
    credential_format = settings.sybol_credential_format or DEFAULT_CREDENTIAL_FORMAT

    claims = build_media_claims(result, rag, evidence_url=evidence_url)
    if catalog_document:
        claims = filter_claims_for_catalog(
            claims, extract_catalog_claim_keys(catalog_document)
        )

    body: dict[str, Any] = {
        "documentId": document_id,
        "issuerKey": issuer_key,
        "recipientDid": recipient_did,
        "claims": claims,
        "format": credential_format,
    }
    if settings.sybol_level_of_assurance is not None:
        body["levelOfAssurance"] = settings.sybol_level_of_assurance
    return body
