from src.api.dependencies import Settings
from src.credentials.catalog_issue_builder import build_catalog_issue_request
from src.rag.models import ComplianceResult, RegulationRef
from src.scoring.models import ComplianceStatus, ScoringResult, SignalBreakdown


def test_build_catalog_issue_request_uses_object_claims():
    settings = Settings(
        sybol_document_id="doc-1",
        sybol_issuer_key="issuer-1",
        sybol_recipient_did="did:example:recipient",
    )
    result = ScoringResult(
        authenticity_score=0.86,
        score_breakdown=SignalBreakdown(m=0.9, a=0.8, v=0.85, p=0.9),
        compliance_status=ComplianceStatus.COMPLIANT,
        media_hash="a" * 64,
        model_version="demo",
    )
    rag = ComplianceResult(
        summary="Summary text",
        regulation_refs=[
            RegulationRef(
                regulation="EU AI Act",
                article="Article 50",
                source_url="https://example.com",
                excerpt="Excerpt",
            )
        ],
    )

    body = build_catalog_issue_request(
        result, rag, settings=settings, evidence_url="https://example.com/audit"
    )

    assert body["recipientDid"] == "did:example:recipient"
    assert isinstance(body["claims"], dict)
    assert body["claims"]["mediaHash"] == "a" * 64
    assert body["claims"]["authenticityScore"] == "0.86"
    assert body["claims"]["evidenceUrl"] == "https://example.com/audit"
    assert body["claims"]["regulationRefs"] == [
        {
            "regulation": "EU AI Act",
            "article": "Article 50",
            "url": "https://example.com",
        }
    ]
