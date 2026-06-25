from .artifacts import score_artifacts
from .detector import load_detector
from .explain import build_signal_reasons
from .metadata import score_metadata
from .models import ScoringResult, SignalBreakdown
from .preprocess import preprocess
from .provenance import rebuild_provenance_index, score_provenance_with_details
from .scorer import build_result
from .visual import score_visual


def load_scoring_pipeline() -> None:
    rebuild_provenance_index()
    load_detector()


def score_image(
    raw_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> ScoringResult:
    preprocessed = preprocess(raw_bytes, filename=filename, content_type=content_type)
    p_score, p_distance, p_match = score_provenance_with_details(preprocessed)
    breakdown = SignalBreakdown(
        m=score_metadata(preprocessed),
        a=score_artifacts(preprocessed),
        v=score_visual(preprocessed),
        p=p_score,
    )
    reasons = build_signal_reasons(preprocessed, breakdown, p_distance, p_match)
    return build_result(
        preprocessed.media_hash,
        breakdown,
        signal_reasons=reasons,
        provenance_distance=p_distance,
    )
