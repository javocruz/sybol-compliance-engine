import { useCallback, useEffect, useState } from 'react';
import { fetchSystemStatus } from '../api/client';
import type { SystemStatusResponse } from '../types/api';
import './Header.css';

const SYBOL_LOGO =
  'https://cdn.sanity.io/images/ja4f7req/production/ea9dc4182ebcac5b1725fc3e01c6b2cae00159d4-203x201.png?w=120';

type ApiStatus = 'loading' | 'connected' | 'degraded' | 'unreachable';

function deriveStatus(data: SystemStatusResponse | null, error: boolean): ApiStatus {
  if (error) return 'unreachable';
  if (!data) return 'loading';
  const core =
    data.api === 'ok' &&
    data.qdrant === 'ok' &&
    data.rag_index_loaded &&
    data.model_loaded;
  return core ? 'connected' : 'degraded';
}

export function Header() {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [apiStatus, setApiStatus] = useState<ApiStatus>('loading');

  const poll = useCallback(async () => {
    try {
      const data = await fetchSystemStatus();
      setStatus(data);
      setApiStatus(deriveStatus(data, false));
    } catch {
      setStatus(null);
      setApiStatus('unreachable');
    }
  }, []);

  useEffect(() => {
    void poll();
    const id = window.setInterval(() => void poll(), 60_000);
    return () => window.clearInterval(id);
  }, [poll]);

  const statusLabel =
    apiStatus === 'loading'
      ? 'Checking…'
      : apiStatus === 'connected'
        ? 'All systems ready'
        : apiStatus === 'degraded'
          ? 'Degraded — see System tab'
          : 'API unreachable';

  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-brand">
          <img src={SYBOL_LOGO} alt="" className="header-logo" width={36} height={36} />
          <div>
            <h1 className="header-title">Sybol</h1>
            <p className="header-sublabel">Compliance Engine</p>
          </div>
        </div>
        <div className={`header-status header-status--${apiStatus}`} aria-live="polite">
          <span className="header-status-dot" aria-hidden="true" />
          <span>{statusLabel}</span>
          {status?.regulations_chunks != null && apiStatus !== 'unreachable' && (
            <span className="header-status-meta">
              {status.regulations_chunks.toLocaleString()} chunks
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
