import type { SystemStatusResponse } from '../types/api';

export function parseSystemStatus(raw: SystemStatusResponse) {
  const isHealthy =
    raw.api === 'ok' &&
    raw.qdrant === 'ok' &&
    raw.rag_index_loaded &&
    raw.model_loaded;

  return {
    isHealthy,
    chunkLabel:
      raw.regulations_chunks != null
        ? raw.regulations_chunks.toLocaleString()
        : '—',
  };
}

export function truncateId(id: string, visible = 12): string {
  if (id.length <= visible * 2 + 3) return id;
  return `${id.slice(0, visible)}…${id.slice(-visible)}`;
}
