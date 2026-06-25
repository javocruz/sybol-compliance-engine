"""Property-based tests for the scoring math (Saba, Step 4).

These complement the example-based assertions in test_scorer.py: instead of a
handful of fixed inputs, Hypothesis generates thousands of signal breakdowns and
checks that the *invariants* of the scorer hold across the input space.

Invariants under test:
  * authenticity score is always clamped to [0, 1]
  * status mapping is monotonic and consistent with the published thresholds
  * provenance-match and synthetic-profile rules behave as documented

Note: after golden-set calibration the score is no longer a pure convex
combination of signals — post-weight floor/cap rules apply in scorer.py.
"""

import math

from hypothesis import assume, given
from hypothesis import strategies as st

from scoring.constants import (
    CAMERA_LIKELY_ARTIFACT_MIN,
    CAMERA_LIKELY_VISUAL_MIN,
    EDITED_PROFILE_ARTIFACT_MAX,
    EDITED_PROFILE_ARTIFACT_MIN,
    EDITED_PROFILE_METADATA_MAX,
    EDITED_PROFILE_METADATA_MIN,
    EDITED_PROFILE_PROVENANCE_MAX,
    EDITED_RESAVED_ARTIFACT_MIN,
    EDITED_RESAVED_METADATA_MAX,
    EDITED_RESAVED_METADATA_MIN,
    EDITED_RESAVED_PROVENANCE_MAX,
    EXIF_RICH_METADATA_MIN,
    PNG_NEUTRAL_METADATA_MAX,
    PNG_NEUTRAL_METADATA_MIN,
    PROVENANCE_MATCH_MIN,
    SYNTHETIC_PROFILE_METADATA_MAX,
    SYNTHETIC_PROFILE_PROVENANCE_MAX,
    THRESHOLD_COMPLIANT,
    THRESHOLD_NON_COMPLIANT,
    WA,
    WM,
    WP,
    WV,
)
from scoring.models import ComplianceStatus, SignalBreakdown
from scoring.scorer import compute_authenticity_score, map_compliance_status

signal = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


def _breakdown(m: float, a: float, v: float, p: float) -> SignalBreakdown:
    return SignalBreakdown(m=m, a=a, v=v, p=p)


def _is_resaved_edited(m: float, a: float, p: float) -> bool:
    return (
        EDITED_RESAVED_METADATA_MIN <= m <= EDITED_RESAVED_METADATA_MAX
        and a >= EDITED_RESAVED_ARTIFACT_MIN
        and p <= EDITED_RESAVED_PROVENANCE_MAX
    )


def _rules_apply(m: float, a: float, v: float, p: float) -> bool:
    if p >= PROVENANCE_MATCH_MIN:
        return True
    if m >= EXIF_RICH_METADATA_MIN:
        return True
    if _is_resaved_edited(m, a, p):
        return True
    if (
        p <= SYNTHETIC_PROFILE_PROVENANCE_MAX
        and not (a >= CAMERA_LIKELY_ARTIFACT_MIN and v >= CAMERA_LIKELY_VISUAL_MIN)
        and (
            m <= SYNTHETIC_PROFILE_METADATA_MAX
            or PNG_NEUTRAL_METADATA_MIN <= m <= PNG_NEUTRAL_METADATA_MAX
        )
    ):
        return True
    if (
        EDITED_PROFILE_METADATA_MIN <= m <= EDITED_PROFILE_METADATA_MAX
        and EDITED_PROFILE_ARTIFACT_MIN <= a <= EDITED_PROFILE_ARTIFACT_MAX
        and p <= EDITED_PROFILE_PROVENANCE_MAX
    ):
        return True
    return False


def test_weights_sum_to_one():
    assert math.isclose(WM + WA + WV + WP, 1.0)


@given(m=signal, a=signal, v=signal, p=signal)
def test_score_always_in_unit_interval(m, a, v, p):
    score = compute_authenticity_score(_breakdown(m, a, v, p))
    assert 0.0 <= score <= 1.0


@given(m=signal, a=signal, v=signal, p=signal)
def test_weighted_average_when_no_post_rules(m, a, v, p):
    assume(not _rules_apply(m, a, v, p))
    expected = WM * m + WA * a + WV * v + WP * p
    assert math.isclose(
        compute_authenticity_score(_breakdown(m, a, v, p)), expected, abs_tol=1e-9
    )


@given(p=st.floats(min_value=PROVENANCE_MATCH_MIN, max_value=1.0, allow_nan=False))
def test_provenance_match_applies_floor(p):
    # Low other signals but strong provenance match must reach the configured floor.
    score = compute_authenticity_score(_breakdown(0.4, 0.4, 0.4, p))
    assert score >= 0.82


@given(
    m=st.floats(
        min_value=0.0, max_value=SYNTHETIC_PROFILE_METADATA_MAX, allow_nan=False
    ),
    p=st.floats(
        min_value=0.0, max_value=SYNTHETIC_PROFILE_PROVENANCE_MAX, allow_nan=False
    ),
)
def test_synthetic_profile_applies_cap(m, p):
    # The re-saved edited carve-out (camera JPEG, stripped EXIF, strong artifacts,
    # no provenance) is intentionally exempt from the synthetic cap and maps to
    # the review band instead. Visual is kept below the camera-likely threshold so
    # the synthetic cap is not skipped.
    assume(not _is_resaved_edited(m, 0.75, p))
    score = compute_authenticity_score(_breakdown(m, 0.75, 0.71, p))
    assert score <= 0.26


@given(
    score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_status_mapping_is_total_and_consistent(score):
    status = map_compliance_status(score)
    if score < THRESHOLD_NON_COMPLIANT:
        assert status == ComplianceStatus.NON_COMPLIANT
    elif score < THRESHOLD_COMPLIANT:
        assert status == ComplianceStatus.REVIEW
    else:
        assert status == ComplianceStatus.COMPLIANT


@given(
    lower=st.floats(
        min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
    ),
    higher=st.floats(
        min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
    ),
)
def test_status_is_monotonic_in_score(lower, higher):
    if lower > higher:
        lower, higher = higher, lower
    rank = {
        ComplianceStatus.NON_COMPLIANT: 0,
        ComplianceStatus.REVIEW: 1,
        ComplianceStatus.COMPLIANT: 2,
    }
    assert rank[map_compliance_status(higher)] >= rank[map_compliance_status(lower)]
