import type { ComplianceStatus } from '../types/api';
import './ComplianceBadge.css';

interface ComplianceBadgeProps {
  status: ComplianceStatus;
}

const LABELS: Record<ComplianceStatus, string> = {
  compliant: 'Compliant',
  review: 'Review',
  'non-compliant': 'Non-compliant',
};

export function ComplianceBadge({ status }: ComplianceBadgeProps) {
  return (
    <span className={`compliance-badge compliance-badge--${status.replace('-', '_')}`}>
      {LABELS[status]}
    </span>
  );
}
