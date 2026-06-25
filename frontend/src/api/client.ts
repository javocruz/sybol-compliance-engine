import type {
  AnalyzeResponse,
  ApiErrorBody,
  HealthResponse,
  IssueResponse,
  LlmProvider,
  QueryResponse,
} from '../types/api';

const base = import.meta.env.VITE_API_BASE_URL ?? '';

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
  const res = await fetch(`${base}/api/issue`, { method: 'POST', body: form });
  if (!res.ok) {
    throw new ApiError(await parseErrorMessage(res), res.status);
  }
  return res.json() as Promise<IssueResponse>;
}
