import { useState } from 'react';
import type { IssueResponse, RegulationRef, VcRegulationRef } from '../types/api';
import { ComplianceBadge } from './ComplianceBadge';
import { AuthenticityGauge } from './AuthenticityGauge';
import { ScoreBreakdownPanel } from './ScoreBreakdown';
import { MetadataRow } from './MetadataRow';
import { RegulationRefs } from './RegulationRefs';
import './CredentialResultsPanel.css';

interface CredentialResultsPanelProps {
  results: IssueResponse;
  onViewAuditRecord?: (recordId: string) => void;
}

function toRegulationRefs(refs: VcRegulationRef[]): RegulationRef[] {
  return refs.map((ref) => ({
    regulation: ref.regulation,
    article: ref.article,
    url: ref.url,
  }));
}

function truncateId(id: string, visible = 12): string {
  if (id.length <= visible * 2 + 3) return id;
  return `${id.slice(0, visible)}…${id.slice(-visible)}`;
}

function recordIdFromEvidenceUrl(url: string): string | null {
  const match = url.match(/\/points\/([^/?#]+)$/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function CredentialResultsPanel({
  results,
  onViewAuditRecord,
}: CredentialResultsPanelProps) {
  const subject = results.vc_payload?.credentialSubject;
  const signed = results.signed_vc;
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copyText = async (field: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      window.setTimeout(() => setCopiedField(null), 2000);
    } catch {
      setCopiedField(null);
    }
  };

  const downloadJson = () => {
    const payload = results.signed_vc ?? results.vc_payload;
    if (!payload) return;
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `vc-${results.vc_id?.replace(/[^a-zA-Z0-9-]/g, '_') ?? 'credential'}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (!subject) {
    return (
      <p className="credential-results-empty">
        Credential issued but payload details are unavailable.
      </p>
    );
  }

  const regulationRefs = toRegulationRefs(subject.regulationRefs);

  return (
    <div className="credential-results">
      <div className="credential-results-header">
        <span
          className={`credential-status-badge${results.signed ? ' credential-status-badge--signed' : ''}`}
        >
          {results.signed ? 'Signed VC' : 'Unsigned VC'}
        </span>
        {results.detail && (
          <span className="credential-detail">{results.detail}</span>
        )}
      </div>

      {results.vc_id && (
        <div className="credential-id-row">
          <span className="credential-id-label">Credential ID</span>
          <code className="credential-id-value" title={results.vc_id}>
            {truncateId(results.vc_id)}
          </code>
          <button
            type="button"
            className="btn btn-secondary credential-copy-btn"
            onClick={() => void copyText('id', results.vc_id!)}
          >
            {copiedField === 'id' ? 'Copied' : 'Copy'}
          </button>
        </div>
      )}

      {signed?.issuer && (
        <div className="credential-issuer-row">
          <span className="credential-id-label">Issuer</span>
          <code className="credential-issuer-value" title={signed.issuer}>
            {truncateId(signed.issuer, 16)}
          </code>
        </div>
      )}

      <div className="credential-results-scores">
        <ComplianceBadge status={subject.complianceStatus} />
        <AuthenticityGauge score={subject.authenticityScore} />
      </div>

      <ScoreBreakdownPanel breakdown={subject.scoreBreakdown} />

      <MetadataRow
        mediaHash={subject.mediaHash}
        modelVersion={subject.modelVersion}
        analysisTimestamp={subject.analysisTimestamp}
      />

      {subject.evidenceUrl && (
        <div className="credential-evidence">
          <span className="credential-id-label">Audit evidence</span>
          {(() => {
            const recordId =
              recordIdFromEvidenceUrl(subject.evidenceUrl) ??
              results.vc_id?.removeprefix('urn:uuid:') ??
              null;
            if (recordId && onViewAuditRecord) {
              return (
                <button
                  type="button"
                  className="credential-evidence-link"
                  onClick={() => onViewAuditRecord(recordId)}
                >
                  View in Audit Trail
                </button>
              );
            }
            return (
              <a
                href={subject.evidenceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="credential-evidence-link"
              >
                View audit record
              </a>
            );
          })()}
        </div>
      )}

      {regulationRefs.length > 0 && (
        <div className="credential-refs">
          <h3 className="credential-refs-heading">
            Regulation citations
            <span className="credential-refs-count">({regulationRefs.length})</span>
          </h3>
          <RegulationRefs refs={regulationRefs} />
        </div>
      )}

      {signed?.proof && (
        <div className="credential-proof">
          <h3 className="credential-proof-heading">Cryptographic proof</h3>
          <dl className="credential-proof-list">
            {signed.proof.type && (
              <div className="credential-proof-item">
                <dt>Type</dt>
                <dd>{signed.proof.type}</dd>
              </div>
            )}
            {signed.proof.created && (
              <div className="credential-proof-item">
                <dt>Created</dt>
                <dd>{new Date(signed.proof.created).toLocaleString()}</dd>
              </div>
            )}
            {signed.proof.proofPurpose && (
              <div className="credential-proof-item">
                <dt>Purpose</dt>
                <dd>{signed.proof.proofPurpose}</dd>
              </div>
            )}
          </dl>
        </div>
      )}

      {signed?.signed_token && (
        <div className="credential-token">
          <span className="credential-id-label">Signed token (JWT)</span>
          <code className="credential-token-value" title={signed.signed_token}>
            {truncateId(signed.signed_token, 20)}
          </code>
          <button
            type="button"
            className="btn btn-secondary credential-copy-btn"
            onClick={() => void copyText('token', signed.signed_token!)}
          >
            {copiedField === 'token' ? 'Copied' : 'Copy token'}
          </button>
        </div>
      )}

      <div className="credential-actions">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() =>
            void copyText(
              'json',
              JSON.stringify(results.signed_vc ?? results.vc_payload, null, 2),
            )
          }
        >
          {copiedField === 'json' ? 'Copied JSON' : 'Copy JSON'}
        </button>
        <button type="button" className="btn btn-secondary" onClick={downloadJson}>
          Download JSON
        </button>
      </div>
    </div>
  );
}
