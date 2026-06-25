"""Build Sybol BusinessWallet CredentialIssueRequest (OpenAPI v4)."""

from src.api.dependencies import Settings
from src.rag.models import ComplianceResult
from src.scoring.models import ScoringResult


def _claim_value(value: object) -> object:
    if isinstance(value, (dict, list)):
        return value
    return str(value)


def build_catalog_issue_request(
    result: ScoringResult,
    rag: ComplianceResult,
    *,
    settings: Settings,
    evidence_url: str | None = None,
) -> dict:
    """
    Map scoring + RAG output to POST /api/bl/credentials body per openapi-wallet.yaml.

    Required fields: documentId, issuerKey, recipientDid, claims.
    Live API validates claims as a flat object (key -> value), not ClaimValue[].
    """
    document_id = settings.sybol_document_id
    issuer_key = settings.sybol_issuer_key
    if not document_id or not issuer_key:
        raise ValueError(
            "SYBOL_DOCUMENT_ID and SYBOL_ISSUER_KEY are required for catalog issuance."
        )

    recipient_did = settings.sybol_recipient_did or settings.sybol_subject_did
    if not recipient_did:
        raise ValueError(
            "SYBOL_RECIPIENT_DID (or SYBOL_SUBJECT_DID) is required for catalog issuance."
        )

    claims: dict[str, object] = {
        "mediaHash": _claim_value(result.media_hash),
        "authenticityScore": _claim_value(result.authenticity_score),
        "complianceStatus": _claim_value(result.compliance_status.value),
        "modelVersion": _claim_value(result.model_version),
        "scoreBreakdown.m": _claim_value(result.score_breakdown.m),
        "scoreBreakdown.a": _claim_value(result.score_breakdown.a),
        "scoreBreakdown.v": _claim_value(result.score_breakdown.v),
        "scoreBreakdown.p": _claim_value(result.score_breakdown.p),
        "regulationRefs": _claim_value(
            [
                {
                    "regulation": r.regulation,
                    "article": r.article,
                    "url": r.source_url,
                }
                for r in rag.regulation_refs
            ]
        ),
        "ragSummary": _claim_value(rag.summary),
    }
    if evidence_url:
        claims["evidenceUrl"] = _claim_value(evidence_url)

    body: dict = {
        "documentId": document_id,
        "issuerKey": issuer_key,
        "recipientDid": recipient_did,
        "claims": claims,
        "format": settings.sybol_credential_format,
    }
    if settings.sybol_level_of_assurance is not None:
        body["levelOfAssurance"] = settings.sybol_level_of_assurance
    return body
