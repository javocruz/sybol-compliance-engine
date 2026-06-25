import { useCallback, useEffect, useState } from 'react';
import { fetchAuditRecord, fetchAuditRecords, ApiError } from '../api/client';
import type { AuditRecord } from '../types/api';
import { LoadingPanel } from './LoadingPanel';
import { ErrorAlert } from './ErrorAlert';
import { AuditRecordPanel } from './AuditRecordPanel';
import './AuditTab.css';

interface AuditTabProps {
  initialRecordId?: string | null;
}

function truncateId(id: string, visible = 8): string {
  if (id.length <= visible * 2 + 3) return id;
  return `${id.slice(0, visible)}…${id.slice(-visible)}`;
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleString();
}

export function AuditTab({ initialRecordId = null }: AuditTabProps) {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(initialRecordId);
  const [selectedRecord, setSelectedRecord] = useState<AuditRecord | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRecords = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const response = await fetchAuditRecords();
      setRecords(response.records);
      setTotal(response.total);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 503) {
          setError(
            `${err.message} Ensure Qdrant is running (see project README).`,
          );
        } else {
          setError(err.message);
        }
      } else if (err instanceof TypeError) {
        setError('Network error — could not reach the API. Is the server running?');
      } else {
        setError('An unexpected error occurred.');
      }
      setRecords([]);
      setTotal(0);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    void loadRecords();
  }, [loadRecords]);

  useEffect(() => {
    if (initialRecordId) {
      setSelectedId(initialRecordId);
    }
  }, [initialRecordId]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedRecord(null);
      return;
    }

    const cached = records.find((record) => record.id === selectedId);
    if (cached) {
      setSelectedRecord(cached);
      return;
    }

    let cancelled = false;
    setLoadingDetail(true);
    void fetchAuditRecord(selectedId)
      .then((record) => {
        if (!cancelled) {
          setSelectedRecord(record);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError('Could not load the selected audit record.');
        }
        setSelectedRecord(null);
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingDetail(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedId, records]);

  return (
    <div className="audit-tab">
      <div className="audit-tab-grid">
        <section className="audit-tab-list card">
          <div className="audit-tab-list-header">
            <h2 className="audit-tab-heading">Audit trail</h2>
            <button
              type="button"
              className="btn btn-secondary audit-tab-refresh"
              onClick={() => void loadRecords()}
              disabled={loadingList}
            >
              Refresh
            </button>
          </div>
          <p className="audit-tab-intro">
            Metadata-only records written when credentials are issued. No raw image
            bytes are stored.
          </p>

          {loadingList && <LoadingPanel title="Loading audit records…" />}
          {error && <ErrorAlert title="Audit trail unavailable" message={error} />}

          {!loadingList && !error && records.length === 0 && (
            <p className="audit-tab-placeholder">
              No audit records yet. Issue a credential on the Issue tab to create one.
            </p>
          )}

          {!loadingList && records.length > 0 && (
            <>
              <p className="audit-tab-count">
                {total} record{total === 1 ? '' : 's'}
              </p>
              <ul className="audit-tab-records">
                {records.map((record) => (
                  <li key={record.id}>
                    <button
                      type="button"
                      className={`audit-tab-record${selectedId === record.id ? ' audit-tab-record--active' : ''}`}
                      onClick={() => setSelectedId(record.id)}
                    >
                      <span className="audit-tab-record-id">
                        {truncateId(record.id)}
                      </span>
                      <span className="audit-tab-record-meta">
                        {formatTimestamp(record.analysis_timestamp)}
                      </span>
                      <span
                        className={`audit-tab-record-status audit-tab-record-status--${record.compliance_status}`}
                      >
                        {record.compliance_status}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="audit-tab-detail card">
          <h2 className="audit-tab-heading">Record detail</h2>
          {loadingDetail && <LoadingPanel title="Loading record…" />}
          {!loadingDetail && selectedRecord ? (
            <AuditRecordPanel record={selectedRecord} />
          ) : (
            !loadingDetail && (
              <p className="audit-tab-placeholder">
                Select a record to view scores, regulation citations, and metadata.
              </p>
            )
          )}
        </section>
      </div>
    </div>
  );
}
