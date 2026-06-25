import type { ScoreBreakdown } from '../types/api';
import { SIGNAL_KEYS, SIGNAL_LABELS } from '../constants/signals';
import './ScoreBreakdown.css';

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdown;
}

export function ScoreBreakdownPanel({ breakdown }: ScoreBreakdownProps) {
  return (
    <div className="score-breakdown">
      <h3 className="score-breakdown-title">Signal breakdown</h3>
      <ul className="score-breakdown-list">
        {SIGNAL_KEYS.map((key) => {
          const value = breakdown[key];
          const percent = Math.round(value * 100);
          const { label, description } = SIGNAL_LABELS[key];

          const reason = breakdown.reasons?.[key];
          return (
            <li key={key} className="score-breakdown-item">
              <div className="score-breakdown-header">
                <span className="score-breakdown-label" title={reason || description}>
                  {label}
                </span>
                <span className="score-breakdown-value">{percent}%</span>
              </div>
              {reason && <p className="score-breakdown-reason">{reason}</p>}
              <div className="score-breakdown-bar" role="presentation">
                <div
                  className="score-breakdown-bar-fill"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
