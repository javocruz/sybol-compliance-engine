from unittest.mock import MagicMock

import pytest

from src.api.dependencies import Settings
from src.credentials.audit import get_audit_record, list_audit_records, write_audit_record
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


def test_list_audit_records_returns_empty_when_collection_missing(settings):
    client = _make_client([])
    records, total = list_audit_records(client, settings)
    assert records == []
    assert total == 0


def test_list_audit_records_sorts_newest_first(scoring_result, compliance_result, settings):
    client = _make_client(["media_audit"])
    older = MagicMock()
    older.id = "older-id"
    older.payload = {
        "mediaHash": "aaa",
        "authenticityScore": 0.5,
        "scoreBreakdown": {"m": 0.5, "a": 0.5, "v": 0.5, "p": 0.5},
        "complianceStatus": "review",
        "modelVersion": "v1.0",
        "analysisTimestamp": "2026-01-01T00:00:00Z",
        "regulationRefs": [],
    }
    newer = MagicMock()
    newer.id = "newer-id"
    newer.payload = {
        "mediaHash": "bbb",
        "authenticityScore": 0.9,
        "scoreBreakdown": {"m": 0.9, "a": 0.9, "v": 0.9, "p": 0.9},
        "complianceStatus": "compliant",
        "modelVersion": "v1.0",
        "analysisTimestamp": "2026-06-01T00:00:00Z",
        "regulationRefs": [],
    }
    client.scroll.return_value = ([older, newer], None)

    records, total = list_audit_records(client, settings)
    assert total == 2
    assert records[0]["id"] == "newer-id"
    assert records[1]["id"] == "older-id"


def test_get_audit_record_returns_none_when_missing(settings):
    client = _make_client(["media_audit"])
    client.retrieve.return_value = []
    assert get_audit_record("missing", client, settings) is None


def test_get_audit_record_returns_formatted_record(scoring_result, compliance_result, settings):
    client = _make_client(["media_audit"])
    point = MagicMock()
    point.id = "abc-123"
    write_audit_record(scoring_result, compliance_result, "urn:uuid:abc-123", client, settings)
    point.payload = client.upsert.call_args.kwargs["points"][0].payload
    client.retrieve.return_value = [point]

    record = get_audit_record("abc-123", client, settings)
    assert record is not None
    assert record["id"] == "abc-123"
    assert record["credential_id"] == "urn:uuid:abc-123"
    assert record["media_hash"] == "deadbeef001122"
    assert record["regulation_refs"][0]["url"] == "https://eur-lex.europa.eu/aiact"
