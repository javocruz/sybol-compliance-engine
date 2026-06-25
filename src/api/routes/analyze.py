from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.api.schemas import AnalyzeResponse, ScoreBreakdown, SignalReasonsSchema
from src.api.upload import read_validated_image
from src.scoring.pipeline import score_image
from src.scoring.preprocess import ScoringError

router = APIRouter(tags=["scoring"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Score media authenticity",
    responses={
        400: {"description": "Unsupported file type or corrupted file"},
        413: {"description": "File exceeds size limit"},
    },
)
async def analyze(
    file: UploadFile = File(...),
):
    content, filename, content_type = await read_validated_image(file)
    try:
        result = score_image(
            content,
            filename=filename,
            content_type=content_type,
        )
    except ScoringError as exc:
        raise HTTPException(400, detail=str(exc)) from exc

    breakdown = result.score_breakdown
    reasons = None
    if result.signal_reasons:
        reasons = SignalReasonsSchema(
            m=result.signal_reasons.m,
            a=result.signal_reasons.a,
            v=result.signal_reasons.v,
            p=result.signal_reasons.p,
        )
    return AnalyzeResponse(
        authenticity_score=result.authenticity_score,
        score_breakdown=ScoreBreakdown(
            m=breakdown.m,
            a=breakdown.a,
            v=breakdown.v,
            p=breakdown.p,
            reasons=reasons,
            provenance_distance=result.provenance_distance,
        ),
        compliance_status=result.compliance_status.value,
        media_hash=result.media_hash,
        model_version=result.model_version,
        analysis_timestamp=datetime.utcnow().isoformat(),
    )
