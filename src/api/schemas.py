from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    metadata: float = Field(..., ge=0.0, le=1.0, alias="m")
    artifact: float = Field(..., ge=0.0, le=1.0, alias="a")
    visual: float = Field(..., ge=0.0, le=1.0, alias="v")
    provenance: float = Field(..., ge=0.0, le=1.0, alias="p")


class AnalyzeResponse(BaseModel):
    authenticity_score: float = Field(..., ge=0.0, le=1.0)
    score_breakdown: ScoreBreakdown
    compliance_status: Literal["compliant", "non-compliant", "review"]
    media_hash: str
    model_version: str
    analysis_timestamp: str
    evidence_url: str | None = None


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    llm_provider: Literal["mistral", "ollama"] = "mistral"


class QueryResponse(BaseModel):
    answer: str
    regulation_refs: list[dict] = Field(default_factory=list)
    llm_provider: str
    llm_model: str


class IssueResponse(BaseModel):
    status: str
    vc_id: str | None = None
    detail: str | None = None
    signed: bool = False
    vc_payload: dict | None = None
    signed_vc: dict | None = None


class AuthLoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class AuthStatusResponse(BaseModel):
    authenticated: bool
    email: str | None = None
    catalog_configured: bool = False
    session_active: bool = False


class AuthLoginResponse(BaseModel):
    authenticated: bool
    email: str | None = None
    catalog_configured: bool = False
    session_active: bool = False


class AuditRegulationRef(BaseModel):
    regulation: str
    article: str
    url: str


class AuditRecordResponse(BaseModel):
    id: str
    credential_id: str
    evidence_url: str
    media_hash: str
    authenticity_score: float = Field(..., ge=0.0, le=1.0)
    score_breakdown: ScoreBreakdown
    compliance_status: Literal["compliant", "non-compliant", "review"]
    model_version: str
    analysis_timestamp: str
    regulation_refs: list[AuditRegulationRef] = Field(default_factory=list)


class AuditListResponse(BaseModel):
    records: list[AuditRecordResponse]
    total: int
    limit: int
    offset: int
