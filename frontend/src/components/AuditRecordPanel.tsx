import type { AuditRecord } from '../types/api';
import { ComplianceBadge } from './ComplianceBadge';
import { AuthenticityGauge } from './AuthenticityGauge';
import { ScoreBreakdownPanel } from './ScoreBreakdown';
import { MetadataRow } from './MetadataRow';
import { RegulationRefs } from './RegulationRefs';
import './AuditRecordPanel.css';

interface AuditRecordPanelProps {
  record: AuditRecord;
}

function truncateId(id: string, visible = 12): string {
  if (id.length <= visible * 2 + 3) return id;
  return `${id.slice(0, visible)}…${id.slice(-visible)}`;
}

export function AuditRecordPanel({ record }: AuditRecordPanelProps) {
  return (
    <div className="audit-record-panel">
      <div className="audit-record-id-row">
        <span className="audit-record-label">Credential ID</span>
        <code className="audit-record-id" title={record.credential_id}>
          {truncateId(record.credential_id)}
        </code>
      </div>

      <div className="audit-record-scores">
        <ComplianceBadge status={record.compliance_status} />
        <AuthenticityGauge score={record.authenticity_score} />
      </div>

      <ScoreBreakdownPanel breakdown={record.score_breakdown} />
      <MetadataRow
        mediaHash={record.media_hash}
        modelVersion={record.model_version}
        analysisTimestamp={record.analysis_timestamp}
      />

      {record.regulation_refs.length > 0 && (
        <div className="audit-record-refs">
          <h3 className="audit-record-refs-heading">
            Regulation citations
            <span className="audit-record-refs-count">
              ({record.regulation_refs.length})
            </span>
          </h3>
          <RegulationRefs refs={record.regulation_refs} />
        </div>
      )}

      <div className="audit-record-evidence">
        <span className="audit-record-label">Evidence URL</span>
        <code className="audit-record-evidence-url" title={record.evidence_url}>
          {truncateId(record.evidence_url, 24)}
        </code>
      </div>
    </div>
  );
}
