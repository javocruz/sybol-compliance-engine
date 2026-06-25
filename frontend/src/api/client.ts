import type {
  AnalyzeResponse,
  ApiErrorBody,
  AuditListResponse,
  AuditRecord,
  AuthLoginResponse,
  AuthStatusResponse,
  HealthResponse,
  IssueResponse,
  LlmProvider,
  QueryResponse,
} from '../types/api';

const base = import.meta.env.VITE_API_BASE_URL ?? '';

const fetchOptions: RequestInit = { credentials: 'include' };

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function parseErrorMessage(res: Response): Promise<string> {
  let message = `Request failed (${res.status})`;
  try {
    const body = (await res.json()) as ApiErrorBody;
    if (typeof body.detail === 'string') {
      message = body.detail;
    } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      message = body.detail[0].msg;
    }
  } catch {
    // Response body was not JSON.
  }
  return message;
}

export async function healthCheck(): Promise<HealthResponse> {
  const res = await fetch(`${base}/health`);
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<HealthResponse>;
}

export async function analyzeImage(file: File): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${base}/api/analyze`, { method: 'POST', body: form });
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<AnalyzeResponse>;
}

export async function queryRegulations(
  question: string,
  llmProvider: LlmProvider = 'mistral',
): Promise<QueryResponse> {
  const res = await fetch(`${base}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, llm_provider: llmProvider }),
  });
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<QueryResponse>;
}

export async function issueCredential(file: File): Promise<IssueResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${base}/api/issue`, {
    method: 'POST',
    body: form,
    credentials: 'include',
  });
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<IssueResponse>;
}

export async function authStatus(): Promise<AuthStatusResponse> {
  const res = await fetch(`${base}/api/auth/status`, fetchOptions);
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<AuthStatusResponse>;
}

export async function authLogin(
  email: string,
  password: string,
): Promise<AuthLoginResponse> {
  const res = await fetch(`${base}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<AuthLoginResponse>;
}

export async function authLogout(): Promise<AuthLoginResponse> {
  const res = await fetch(`${base}/api/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<AuthLoginResponse>;
}

export async function fetchAuditRecords(
  limit = 50,
  offset = 0,
): Promise<AuditListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const res = await fetch(`${base}/api/audit?${params.toString()}`);
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<AuditListResponse>;
}

export async function fetchAuditRecord(recordId: string): Promise<AuditRecord> {
  const res = await fetch(`${base}/api/audit/${encodeURIComponent(recordId)}`);
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<AuditRecord>;
}
