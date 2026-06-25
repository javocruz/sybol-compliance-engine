import type { AnalyzeResponse } from '../types/api';
import { ComplianceBadge } from './ComplianceBadge';
import { AuthenticityGauge } from './AuthenticityGauge';
import { ScoreBreakdownPanel } from './ScoreBreakdown';
import { MetadataRow } from './MetadataRow';
import './ResultsPanel.css';

interface ResultsPanelProps {
  results: AnalyzeResponse;
}

export function ResultsPanel({ results }: ResultsPanelProps) {
  return (
    <div className="results-panel">
      <div className="results-panel-header">
        <ComplianceBadge status={results.compliance_status} />
      </div>
      <AuthenticityGauge score={results.authenticity_score} />
      <ScoreBreakdownPanel breakdown={results.score_breakdown} />
      <MetadataRow
        mediaHash={results.media_hash}
        modelVersion={results.model_version}
        analysisTimestamp={results.analysis_timestamp}
      />
    </div>
  );
}
