import type {
  AnalyzeResponse,
  ApiErrorBody,
  HealthResponse,
  IssueResponse,
  LlmProvider,
  QueryResponse,
  SystemStatusResponse,
  VerifyResponse,
} from '../types/api';

const base = import.meta.env.VITE_API_BASE_URL ?? '';
const apiKey = import.meta.env.VITE_API_KEY ?? '';

function writeHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  if (apiKey) {
    headers.set('X-API-Key', apiKey);
  }
  return headers;
}

export class ApiError extends Error {
  status?: number;
  retryAfter?: number;

  constructor(message: string, status?: number, retryAfter?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.retryAfter = retryAfter;
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

function parseRetryAfter(res: Response): number | undefined {
  const raw = res.headers.get('Retry-After');
  if (!raw) return undefined;
  const seconds = parseInt(raw, 10);
  return Number.isFinite(seconds) ? seconds : undefined;
}

async function throwApiError(res: Response): Promise<never> {
  const message = await parseErrorMessage(res);
  const retryAfter = parseRetryAfter(res);
  let fullMessage = message;
  if (res.status === 429 && retryAfter != null) {
    fullMessage = `${message} Try again in ${retryAfter}s.`;
  }
  throw new ApiError(fullMessage, res.status, retryAfter);
}

export async function healthCheck(): Promise<HealthResponse> {
  const res = await fetch(`${base}/health`);
  if (!res.ok) {
    await throwApiError(res);
  }
  return res.json() as Promise<HealthResponse>;
}

export async function fetchSystemStatus(): Promise<SystemStatusResponse> {
  const res = await fetch(`${base}/api/status`);
  if (!res.ok) {
    await throwApiError(res);
  }
  return res.json() as Promise<SystemStatusResponse>;
}

export async function analyzeImage(file: File): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${base}/api/analyze`, { method: 'POST', body: form });
  if (!res.ok) {
    await throwApiError(res);
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
    await throwApiError(res);
  }
  return res.json() as Promise<QueryResponse>;
}

export async function issueCredential(file: File): Promise<IssueResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${base}/api/issue`, {
    method: 'POST',
    headers: writeHeaders(),
    body: form,
  });
  if (!res.ok) {
    await throwApiError(res);
  }
  return res.json() as Promise<IssueResponse>;
}

export async function fetchVerifyCredential(vcId: string): Promise<VerifyResponse> {
  const encoded = encodeURIComponent(vcId);
  const res = await fetch(`${base}/api/verify/${encoded}`);
  if (!res.ok) {
    await throwApiError(res);
  }
  return res.json() as Promise<VerifyResponse>;
}

/** @deprecated Use fetchVerifyCredential */
export const fetchVerify = fetchVerifyCredential;
