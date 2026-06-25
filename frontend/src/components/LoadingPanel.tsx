import './LoadingPanel.css';

interface LoadingPanelProps {
  title?: string;
  hint?: string;
}

export function LoadingPanel({
  title = 'Analyzing image…',
  hint = 'First analysis may take 15–30s while the ML model loads.',
}: LoadingPanelProps) {
  return (
    <div className="loading-panel" role="status" aria-live="polite">
      <div className="loading-spinner" aria-hidden="true" />
      <p className="loading-title">{title}</p>
      {hint && <p className="loading-hint">{hint}</p>}
    </div>
  );
}
