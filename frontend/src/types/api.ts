export type ComplianceStatus = 'compliant' | 'non-compliant' | 'review';

export interface ScoreBreakdown {
  m: number;
  a: number;
  v: number;
  p: number;
  reasons?: {
    m: string;
    a: string;
    v: string;
    p: string;
  } | null;
  provenance_distance?: number | null;
}

export interface AnalyzeResponse {
  authenticity_score: number;
  score_breakdown: ScoreBreakdown;
  compliance_status: ComplianceStatus;
  media_hash: string;
  model_version: string;
  analysis_timestamp: string;
  evidence_url?: string | null;
}

export interface HealthResponse {
  status: string;
}

export interface SystemStatusResponse {
  api: string;
  qdrant: string;
  rag_index_loaded: boolean;
  regulations_chunks: number | null;
  sybol_configured: boolean;
  model_loaded: boolean;
  public_base_url: string | null;
  git_commit?: string | null;
  uptime_seconds?: number | null;
  platt_enabled?: boolean;
  vc_version?: string;
  app_env?: string;
}

export type LlmProvider = 'mistral' | 'ollama';

export interface RegulationRef {
  regulation: string;
  article: string;
  url: string;
}

export interface QueryResponse {
  answer: string;
  regulation_refs: RegulationRef[];
  llm_provider: LlmProvider;
  llm_model: string;
}

export interface ApiErrorBody {
  detail?: string | { msg?: string }[];
}

export interface VcRegulationRef {
  regulation: string;
  article: string;
  url: string;
}

export interface VcCredentialSubject {
  id: string;
  mediaHash: string;
  authenticityScore: number;
  scoreBreakdown: ScoreBreakdown;
  complianceStatus: ComplianceStatus;
  modelVersion: string;
  analysisTimestamp: string;
  regulationRefs: VcRegulationRef[];
  evidenceUrl?: string | null;
}

export interface VcPayload {
  '@context': string[];
  id: string;
  type: string[];
  issuanceDate: string;
  expirationDate?: string;
  credentialSubject: VcCredentialSubject;
}

export interface SignedVcProof {
  type?: string;
  created?: string;
  verificationMethod?: string;
  proofPurpose?: string;
  proofValue?: string;
}

export interface SignedVc {
  id?: string;
  issuer?: string;
  signed_token?: string;
  proof?: SignedVcProof;
  credentialStatus?: {
    type?: string;
    statusPurpose?: string;
  };
  [key: string]: unknown;
}

export interface IssueResponse {
  status: string;
  vc_id: string | null;
  detail: string | null;
  signed: boolean;
  vc_payload: VcPayload | null;
  signed_vc: SignedVc | null;
  evidence_url?: string | null;
}

export interface VerifyResponse {
  vc_id: string;
  valid: boolean;
  revoked: boolean;
  audit_found: boolean;
  detail?: string | null;
}
