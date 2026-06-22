from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.api.schemas import AnalyzeResponse, ScoreBreakdown
from src.scoring.pipeline import score_image
from src.scoring.preprocess import ScoringError

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Score media authenticity",
    responses={
        400: {"description": "Unsupported file type or corrupted file"},
    },
)
async def analyze(file: UploadFile = File(...)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Unsupported file type")

    content = await file.read()
    try:
        result = score_image(
            content,
            filename=file.filename,
            content_type=file.content_type,
        )
    except ScoringError as exc:
        raise HTTPException(400, detail=str(exc)) from exc

    breakdown = result.score_breakdown
    return AnalyzeResponse(
        authenticity_score=result.authenticity_score,
        score_breakdown=ScoreBreakdown(
            m=breakdown.m,
            a=breakdown.a,
            v=breakdown.v,
            p=breakdown.p,
        ),
        compliance_status=result.compliance_status.value,
        media_hash=result.media_hash,
        model_version=result.model_version,
        analysis_timestamp=datetime.utcnow().isoformat(),
    )
