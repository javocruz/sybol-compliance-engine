from .constants import (
    CAMERA_LIKELY_ARTIFACT_MIN,
    CAMERA_LIKELY_VISUAL_MIN,
    EDITED_PROFILE_ARTIFACT_MAX,
    EDITED_PROFILE_ARTIFACT_MIN,
    EDITED_PROFILE_METADATA_MAX,
    EDITED_PROFILE_METADATA_MIN,
    EDITED_PROFILE_PROVENANCE_MAX,
    EDITED_PROFILE_SCORE_MAX,
    EDITED_PROFILE_SCORE_MIN,
    EXIF_RICH_METADATA_MIN,
    EXIF_RICH_SCORE_FLOOR,
    PNG_NEUTRAL_METADATA_MAX,
    PNG_NEUTRAL_METADATA_MIN,
    PLATT_ENABLED,
    PLATT_PARAMS_PATH,
    PROVENANCE_MATCH_MIN,
    PROVENANCE_MATCH_SCORE_FLOOR,
    SYNTHETIC_PROFILE_METADATA_MAX,
    SYNTHETIC_PROFILE_PROVENANCE_MAX,
    SYNTHETIC_PROFILE_SCORE_CAP,
    THRESHOLD_COMPLIANT,
    THRESHOLD_NON_COMPLIANT,
    WA,
    WM,
    WP,
    WV,
)
from .detector import get_deepfake_model
from .models import ComplianceStatus, ScoringResult, SignalBreakdown

_platt_params: tuple[float, float] | None = None


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _load_platt_params() -> tuple[float, float] | None:
    global _platt_params
    if _platt_params is not None:
        return _platt_params
    if not PLATT_PARAMS_PATH.exists():
        return None
    import json

    data = json.loads(PLATT_PARAMS_PATH.read_text())
    _platt_params = (float(data["a"]), float(data["b"]))
    return _platt_params


def calibrate(raw_score: float) -> float:
    if not PLATT_ENABLED:
        return raw_score
    params = _load_platt_params()
    if params is None:
        return raw_score
    import math

    a, b = params
    return _clamp(1.0 / (1.0 + math.exp(a * raw_score + b)))


def _camera_likely(breakdown: SignalBreakdown) -> bool:
    return (
        breakdown.a >= CAMERA_LIKELY_ARTIFACT_MIN
        and breakdown.v >= CAMERA_LIKELY_VISUAL_MIN
    )


def _apply_profile_rules(raw: float, breakdown: SignalBreakdown) -> float:
    m, a, v, p = breakdown.m, breakdown.a, breakdown.v, breakdown.p

    if p >= PROVENANCE_MATCH_MIN:
        raw = max(raw, PROVENANCE_MATCH_SCORE_FLOOR)

    if m >= EXIF_RICH_METADATA_MIN:
        raw = max(raw, EXIF_RICH_SCORE_FLOOR)

    if (
        EDITED_PROFILE_METADATA_MIN <= m <= EDITED_PROFILE_METADATA_MAX
        and EDITED_PROFILE_ARTIFACT_MIN <= a <= EDITED_PROFILE_ARTIFACT_MAX
        and p <= EDITED_PROFILE_PROVENANCE_MAX
    ):
        raw = max(EDITED_PROFILE_SCORE_MIN, min(raw, EDITED_PROFILE_SCORE_MAX))

    # Weak provenance + low or PNG-neutral metadata — cap unless camera signals say otherwise.
    if p <= SYNTHETIC_PROFILE_PROVENANCE_MAX and not _camera_likely(breakdown):
        low_metadata = m <= SYNTHETIC_PROFILE_METADATA_MAX
        png_neutral = PNG_NEUTRAL_METADATA_MIN <= m <= PNG_NEUTRAL_METADATA_MAX
        if low_metadata or png_neutral:
            raw = min(raw, SYNTHETIC_PROFILE_SCORE_CAP)

    return raw


def compute_authenticity_score(breakdown: SignalBreakdown) -> float:
    raw = WM * breakdown.m + WA * breakdown.a + WV * breakdown.v + WP * breakdown.p
    raw = _apply_profile_rules(raw, breakdown)
    return _clamp(calibrate(raw))


def map_compliance_status(score: float) -> ComplianceStatus:
    if score < THRESHOLD_NON_COMPLIANT:
        return ComplianceStatus.NON_COMPLIANT
    if score < THRESHOLD_COMPLIANT:
        return ComplianceStatus.REVIEW
    return ComplianceStatus.COMPLIANT


def build_result(media_hash: str, breakdown: SignalBreakdown) -> ScoringResult:
    authenticity_score = compute_authenticity_score(breakdown)
    try:
        model_version = get_deepfake_model().version
    except Exception:
        model_version = "dima806/deepfake_vs_real_image_detection@unloaded"

    return ScoringResult(
        authenticity_score=authenticity_score,
        score_breakdown=breakdown,
        compliance_status=map_compliance_status(authenticity_score),
        media_hash=media_hash,
        model_version=model_version,
    )
