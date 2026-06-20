"""Build Sybol BusinessWallet CredentialIssueRequest (OpenAPI v4)."""

import json

from src.api.dependencies import Settings
from src.rag.models import ComplianceResult
from src.scoring.models import ScoringResult


def _claim(key: str, value: object) -> dict[str, str]:
    if isinstance(value, (dict, list)):
        return {"key": key, "value": json.dumps(value, separators=(",", ":"))}
    return {"key": key, "value": str(value)}


def build_catalog_issue_request(
    result: ScoringResult,
    rag: ComplianceResult,
    *,
    settings: Settings,
    evidence_url: str | None = None,
) -> dict:
    """
    Map scoring + RAG output to POST /api/bl/credentials body per openapi-wallet.yaml.

    Required fields: documentId, issuerKey, subject, claims.
    """
    document_id = settings.sybol_document_id
    issuer_key = settings.sybol_issuer_key
    if not document_id or not issuer_key:
        raise ValueError(
            "SYBOL_DOCUMENT_ID and SYBOL_ISSUER_KEY are required for catalog issuance."
        )

    subject = settings.sybol_subject_did or f"urn:media:{result.media_hash}"

    claims = [
        _claim("mediaHash", result.media_hash),
        _claim("authenticityScore", result.authenticity_score),
        _claim("complianceStatus", result.compliance_status.value),
        _claim("modelVersion", result.model_version),
        _claim("scoreBreakdown.m", result.score_breakdown.m),
        _claim("scoreBreakdown.a", result.score_breakdown.a),
        _claim("scoreBreakdown.v", result.score_breakdown.v),
        _claim("scoreBreakdown.p", result.score_breakdown.p),
        _claim(
            "regulationRefs",
            [
                {
                    "regulation": r.regulation,
                    "article": r.article,
                    "url": r.source_url,
                }
                for r in rag.regulation_refs
            ],
        ),
        _claim("ragSummary", rag.summary),
    ]
    if evidence_url:
        claims.append(_claim("evidenceUrl", evidence_url))

    body: dict = {
        "documentId": document_id,
        "issuerKey": issuer_key,
        "subject": subject,
        "claims": claims,
        "format": "w3c-vc",
    }
    if settings.sybol_level_of_assurance is not None:
        body["levelOfAssurance"] = settings.sybol_level_of_assurance
    return body
