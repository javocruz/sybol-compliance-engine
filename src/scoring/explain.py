from .models import SignalBreakdown, SignalReasons
from .preprocess import PreprocessedImage


def build_signal_reasons(
    preprocessed: PreprocessedImage,
    breakdown: SignalBreakdown,
    provenance_distance: int | None,
    provenance_match: str | None,
) -> SignalReasons:
    m_reason = _metadata_reason(preprocessed, breakdown.m)
    a_reason = _artifact_reason(breakdown.a)
    v_reason = _visual_reason(breakdown.v)
    p_reason = _provenance_reason(breakdown.p, provenance_distance, provenance_match)
    return SignalReasons(m=m_reason, a=a_reason, v=v_reason, p=p_reason)


def _metadata_reason(preprocessed: PreprocessedImage, score: float) -> str:
    if score >= 0.72:
        return "Rich EXIF metadata (camera make/model and capture time present)."
    if score <= 0.35:
        return "Little or no EXIF metadata — common for stripped JPEGs or synthetic exports."
    fmt = (preprocessed.content_type or "").split("/")[-1].upper()
    if fmt in ("PNG", "WEBP"):
        return "PNG/WebP without EXIF — treated as neutral, not stripped-camera evidence."
    return "Partial metadata present; may indicate editing or re-export."


def _artifact_reason(score: float) -> str:
    if score >= 0.75:
        return "Low generation/compression artifacts — consistent with camera capture."
    if score <= 0.35:
        return "Strong synthetic or heavy edit artifacts detected."
    return "Moderate artifact signals — mixed or lightly edited content."


def _visual_reason(score: float) -> str:
    if score >= 0.72:
        return "Visual CNN classifies image as likely real."
    if score <= 0.35:
        return "Visual CNN classifies image as likely AI-generated or deepfake."
    return "Visual authenticity signal is inconclusive."


def _provenance_reason(
    score: float, distance: int | None, match_name: str | None
) -> str:
    if match_name and distance is not None:
        return f"Near-match to authentic reference '{match_name}' (pHash distance {distance})."
    if distance is not None and distance <= 20:
        return f"Close to known authentic set (pHash distance {distance}), no exact match."
    if score >= 0.9:
        return "Strong provenance match in authentic reference index."
    if score <= 0.3:
        return "No match in authentic reference index — unknown or synthetic origin."
    return "Weak or distant provenance match; origin uncertain."
