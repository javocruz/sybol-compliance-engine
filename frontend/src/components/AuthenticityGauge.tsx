import './AuthenticityGauge.css';

interface AuthenticityGaugeProps {
  score: number;
}

export function AuthenticityGauge({ score }: AuthenticityGaugeProps) {
  const percent = Math.round(score * 100);
  const circumference = 2 * Math.PI * 54;
  const offset = circumference * (1 - score);

  return (
    <div className="authenticity-gauge">
      <svg className="authenticity-gauge-ring" viewBox="0 0 120 120" aria-hidden="true">
        <circle className="authenticity-gauge-track" cx="60" cy="60" r="54" />
        <circle
          className="authenticity-gauge-fill"
          cx="60"
          cy="60"
          r="54"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="authenticity-gauge-value">
        <span className="authenticity-gauge-score">{score.toFixed(2)}</span>
        <span className="authenticity-gauge-label">{percent}% authentic</span>
      </div>
    </div>
  );
}
