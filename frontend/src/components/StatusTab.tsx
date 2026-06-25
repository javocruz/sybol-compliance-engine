import { useCallback, useEffect, useState } from 'react';
import { fetchSystemStatus, ApiError } from '../api/client';
import type { SystemStatusResponse } from '../types/api';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { Banner } from './ui/Banner';
import { ErrorAlert } from './ErrorAlert';
import './StatusTab.css';

function StatusCard({
  label,
  value,
  ok,
}: {
  label: string;
  value: string;
  ok?: boolean;
}) {
  return (
    <Card className="status-card">
      <span className="status-card__label">{label}</span>
      <span
        className={`status-card__value${ok === true ? ' status-card__value--ok' : ''}${ok === false ? ' status-card__value--bad' : ''}`}
      >
        {value}
      </span>
    </Card>
  );
}

export function StatusTab() {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSystemStatus();
      setStatus(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Could not reach the API.');
      }
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const allGreen =
    status &&
    status.api === 'ok' &&
    status.qdrant === 'ok' &&
    status.rag_index_loaded &&
    status.model_loaded;

  return (
    <div className="status-tab">
      <div className="status-tab__header">
        <h2 className="status-tab__title">System status</h2>
        <Button variant="secondary" onClick={() => void load()} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </Button>
      </div>

      {error && <ErrorAlert message={error} />}
      {allGreen && (
        <Banner title="All systems operational">
          API, Qdrant, RAG index, and scoring model are ready.
        </Banner>
      )}

      {status && (
        <div className="status-tab__grid">
          <StatusCard label="API" value={status.api} ok={status.api === 'ok'} />
          <StatusCard
            label="Qdrant"
            value={status.qdrant}
            ok={status.qdrant === 'ok'}
          />
          <StatusCard
            label="Regulation chunks"
            value={status.regulations_chunks?.toLocaleString() ?? '—'}
          />
          <StatusCard
            label="RAG index"
            value={status.rag_index_loaded ? 'Loaded' : 'Not loaded'}
            ok={status.rag_index_loaded}
          />
          <StatusCard
            label="Scoring model"
            value={status.model_loaded ? 'Loaded' : 'Not loaded'}
            ok={status.model_loaded}
          />
          <StatusCard
            label="Sybol signing"
            value={status.sybol_configured ? 'Configured' : 'Not configured'}
            ok={status.sybol_configured}
          />
          <StatusCard label="Git commit" value={status.git_commit ?? '—'} />
          <StatusCard
            label="Uptime"
            value={
              status.uptime_seconds != null
                ? `${Math.floor(status.uptime_seconds / 60)}m ${Math.round(status.uptime_seconds % 60)}s`
                : '—'
            }
          />
          <StatusCard
            label="Platt scaling"
            value={status.platt_enabled ? 'Enabled' : 'Disabled'}
          />
          <StatusCard label="VC version" value={status.vc_version ?? '—'} />
          <StatusCard
            label="Public base URL"
            value={status.public_base_url ?? 'Not set'}
          />
        </div>
      )}
    </div>
  );
}
