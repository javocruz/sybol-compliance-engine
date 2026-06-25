import { describe, expect, it } from 'vitest';
import { parseSystemStatus } from './status';

describe('parseSystemStatus', () => {
  it('parses core fields', () => {
    const data = parseSystemStatus({
      api: 'ok',
      qdrant: 'ok',
      rag_index_loaded: true,
      regulations_chunks: 1773,
      sybol_configured: true,
      model_loaded: true,
      public_base_url: 'http://example.com',
    });
    expect(data.isHealthy).toBe(true);
    expect(data.chunkLabel).toBe('1,773');
  });

  it('detects degraded state', () => {
    const data = parseSystemStatus({
      api: 'ok',
      qdrant: 'ok',
      rag_index_loaded: false,
      regulations_chunks: null,
      sybol_configured: false,
      model_loaded: false,
      public_base_url: null,
    });
    expect(data.isHealthy).toBe(false);
  });
});
