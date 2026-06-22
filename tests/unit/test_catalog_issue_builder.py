from src.api.dependencies import Settings
from src.credentials.catalog_issue_builder import (
    build_catalog_issue_request,
    build_media_claims,
    filter_claims_for_catalog,
)
from src.rag.models import ComplianceResult, RegulationRef
from src.scoring.models import ComplianceStatus, ScoringResult, SignalBreakdown


def _scoring_result() -> ScoringResult:
    return ScoringResult(
        authenticity_score=0.86,
        score_breakdown=SignalBreakdown(m=0.9, a=0.8, v=0.85, p=0.9),
        compliance_status=ComplianceStatus.COMPLIANT,
        media_hash="abc" * 21 + "a",
        model_version="v1",
    )


def _rag() -> ComplianceResult:
    return ComplianceResult(
        summary="Summary",
        regulation_refs=[
            RegulationRef(
                regulation="GDPR",
                article="5",
                source_url="https://example.com",
                excerpt="Lawful processing.",
            )
        ],
    )


def test_build_catalog_issue_request_live_api_shape():
    settings = Settings(
        sybol_document_id="doc-1",
        sybol_issuer_key="issuer-key",
        sybol_recipient_did="did:web:example:tenant",
        sybol_credential_format="jwt_vc_json",
        sybol_level_of_assurance=2,
    )
    body = build_catalog_issue_request(_scoring_result(), _rag(), settings=settings)

    assert body["documentId"] == "doc-1"
    assert body["issuerKey"] == "issuer-key"
    assert body["recipientDid"] == "did:web:example:tenant"
    assert body["format"] == "jwt_vc_json"
    assert body["levelOfAssurance"] == 2
    assert "subject" not in body
    assert isinstance(body["claims"], dict)
    assert "mediaHash" in body["claims"]


def test_filter_claims_maps_to_catalog_keys():
    full = build_media_claims(_scoring_result(), _rag(), evidence_url="https://x")
    filtered = filter_claims_for_catalog(full, ["cifSybol"])
    assert list(filtered.keys()) == ["cifSybol"]
    assert len(filtered["cifSybol"]) == 64
