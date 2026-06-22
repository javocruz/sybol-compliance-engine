from scoring.models import ComplianceStatus, SignalBreakdown
from scoring.scorer import (
    build_result,
    calibrate,
    compute_authenticity_score,
    map_compliance_status,
)


def test_calibrate_passthrough_when_platt_disabled():
    assert calibrate(0.42) == 0.42


def test_compute_authenticity_score_weighted_sum():
    breakdown = SignalBreakdown(m=1.0, a=1.0, v=1.0, p=1.0)
    assert compute_authenticity_score(breakdown) == 1.0

    breakdown = SignalBreakdown(m=0.0, a=0.0, v=0.0, p=0.0)
    assert compute_authenticity_score(breakdown) == 0.0

    # Synthetic profile cap: weak metadata + no provenance match.
    breakdown = SignalBreakdown(m=0.2, a=0.75, v=1.0, p=0.1)
    assert compute_authenticity_score(breakdown) == 0.26

    # PNG-neutral metadata + weak provenance — cap unless camera-likely.
    breakdown = SignalBreakdown(m=0.46, a=0.85, v=0.75, p=0.0)
    assert compute_authenticity_score(breakdown) > 0.26

    # Edited profile clamp (TC-003 ready).
    breakdown = SignalBreakdown(m=0.55, a=0.55, v=0.6, p=0.4)
    assert 0.35 <= compute_authenticity_score(breakdown) <= 0.65


def test_map_compliance_status_boundaries():
    assert map_compliance_status(0.0) == ComplianceStatus.NON_COMPLIANT
    assert map_compliance_status(0.29) == ComplianceStatus.NON_COMPLIANT
    assert map_compliance_status(0.3) == ComplianceStatus.REVIEW
    assert map_compliance_status(0.69) == ComplianceStatus.REVIEW
    assert map_compliance_status(0.7) == ComplianceStatus.COMPLIANT
    assert map_compliance_status(1.0) == ComplianceStatus.COMPLIANT


def test_build_result(mock_deepfake_model):
    breakdown = SignalBreakdown(m=0.8, a=0.9, v=0.7, p=0.6)
    result = build_result("hash123", breakdown)
    assert result.media_hash == "hash123"
    assert 0.0 <= result.authenticity_score <= 1.0
    assert result.compliance_status == ComplianceStatus.COMPLIANT
    assert "dima806" in result.model_version
