from enum import Enum

from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non-compliant"
    REVIEW = "review"


class SignalBreakdown(BaseModel):
    m: float = Field(ge=0.0, le=1.0)
    a: float = Field(ge=0.0, le=1.0)
    v: float = Field(ge=0.0, le=1.0)
    p: float = Field(ge=0.0, le=1.0)


class SignalReasons(BaseModel):
    m: str = ""
    a: str = ""
    v: str = ""
    p: str = ""


class ScoringResult(BaseModel):
    authenticity_score: float = Field(ge=0.0, le=1.0)
    score_breakdown: SignalBreakdown
    compliance_status: ComplianceStatus
    media_hash: str
    model_version: str
    signal_reasons: SignalReasons | None = None
    provenance_distance: int | None = None
