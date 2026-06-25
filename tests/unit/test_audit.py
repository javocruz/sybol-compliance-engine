from unittest.mock import MagicMock

import pytest

from src.api.dependencies import Settings
from src.credentials.audit import build_evidence_url, write_audit_record
from src.rag.models import ComplianceResult, RegulationRef
from src.scoring.models import ComplianceStatus, ScoringResult, SignalBreakdown


@pytest.fixture
def scoring_result():
    return ScoringResult(
        authenticity_score=0.75,
        score_breakdown=SignalBreakdown(m=0.8, a=0.7, v=0.75, p=0.75),
        compliance_status=ComplianceStatus.REVIEW,
        media_hash="deadbeef001122",
        model_version="v1.0",
    )


@pytest.fixture
def compliance_result():
    return ComplianceResult(
        summary="Review required.",
        regulationRefs=[
            RegulationRef(
                regulation="AI Act",
                article="13",
                sourceUrl="https://eur-lex.europa.eu/aiact",
                excerpt="Article 13 requires transparency.",
            )
        ],
    )


@pytest.fixture
def settings():
    return Settings(
        qdrant_url="http://localhost:6333",
        qdrant_audit_collection="media_audit",
    )


def _make_client(collection_names: list[str]) -> MagicMock:
    client = MagicMock()
    collection_mocks = [MagicMock(name=n) for n in collection_names]
    for mock, name in zip(collection_mocks, collection_names):
        mock.name = name
    client.get_collections.return_value.collections = collection_mocks
    return client


def test_creates_collection_when_missing(scoring_result, compliance_result, settings):
    client = _make_client([])
    write_audit_record(
        scoring_result, compliance_result, "urn:uuid:abc-123", client, settings
    )
    client.create_collection.assert_called_once()
    create_kwargs = client.create_collection.call_args
    assert create_kwargs.kwargs["collection_name"] == "media_audit"


def test_skips_create_when_collection_exists(
    scoring_result, compliance_result, settings
):
    client = _make_client(["media_audit"])
    write_audit_record(
        scoring_result, compliance_result, "urn:uuid:abc-123", client, settings
    )
    client.create_collection.assert_not_called()


def test_upserts_one_point(scoring_result, compliance_result, settings):
    client = _make_client(["media_audit"])
    write_audit_record(
        scoring_result, compliance_result, "urn:uuid:abc-123", client, settings
    )
    client.upsert.assert_called_once()
    upsert_kwargs = client.upsert.call_args
    assert upsert_kwargs.kwargs["collection_name"] == "media_audit"
    points = upsert_kwargs.kwargs["points"]
    assert len(points) == 1
    assert points[0].id == "abc-123"


def test_point_payload_contains_required_fields(
    scoring_result, compliance_result, settings
):
    client = _make_client(["media_audit"])
    write_audit_record(
        scoring_result, compliance_result, "urn:uuid:abc-123", client, settings
    )
    payload = client.upsert.call_args.kwargs["points"][0].payload
    assert payload["mediaHash"] == "deadbeef001122"
    assert payload["authenticityScore"] == 0.75
    assert payload["complianceStatus"] == "review"
    assert payload["modelVersion"] == "v1.0"
    assert "scoreBreakdown" in payload
    assert "analysisTimestamp" in payload


def test_no_raw_image_bytes_in_payload(scoring_result, compliance_result, settings):
    client = _make_client(["media_audit"])
    write_audit_record(
        scoring_result, compliance_result, "urn:uuid:abc-123", client, settings
    )
    payload = client.upsert.call_args.kwargs["points"][0].payload
    for value in payload.values():
        assert not isinstance(value, (bytes, bytearray)), "Raw bytes must not be stored"


def test_regulation_refs_use_url_key(scoring_result, compliance_result, settings):
    client = _make_client(["media_audit"])
    write_audit_record(
        scoring_result, compliance_result, "urn:uuid:abc-123", client, settings
    )
    refs = client.upsert.call_args.kwargs["points"][0].payload["regulationRefs"]
    assert refs[0]["url"] == "https://eur-lex.europa.eu/aiact"
    assert "sourceUrl" not in refs[0]


def test_returns_url_containing_point_id(scoring_result, compliance_result, settings):
    client = _make_client(["media_audit"])
    url = write_audit_record(
        scoring_result, compliance_result, "urn:uuid:abc-123", client, settings
    )
    assert "abc-123" in url
    assert "media_audit" in url
    assert url.startswith("http://localhost:6333")


def test_returns_public_url_when_configured(scoring_result, compliance_result):
    settings = Settings(
        qdrant_url="http://127.0.0.1:6333",
        qdrant_audit_collection="media_audit",
        public_base_url="http://54.154.92.29:8000",
    )
    client = _make_client(["media_audit"])
    url = write_audit_record(
        scoring_result, compliance_result, "urn:uuid:abc-123", client, settings
    )
    assert url == "http://54.154.92.29:8000/api/audit/abc-123"


def test_build_evidence_url_public():
    settings = Settings(public_base_url="http://example.com:8000/")
    assert (
        build_evidence_url("pt-1", settings)
        == "http://example.com:8000/api/audit/pt-1"
    )


def test_build_evidence_url_qdrant_fallback():
    settings = Settings(
        qdrant_url="http://localhost:6333",
        qdrant_audit_collection="media_audit",
    )
    url = build_evidence_url("pt-1", settings)
    assert url == "http://localhost:6333/collections/media_audit/points/pt-1"
