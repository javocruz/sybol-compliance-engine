import { useEffect, useState } from 'react';
import { healthCheck } from '../api/client';
import './Header.css';

export function Header() {
  const [apiStatus, setApiStatus] = useState<'loading' | 'connected' | 'unreachable'>('loading');

  useEffect(() => {
    let cancelled = false;

    healthCheck()
      .then(() => {
        if (!cancelled) setApiStatus('connected');
      })
      .catch(() => {
        if (!cancelled) setApiStatus('unreachable');
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const statusLabel =
    apiStatus === 'loading'
      ? 'Checking API…'
      : apiStatus === 'connected'
        ? 'API connected'
        : 'API unreachable';

  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-brand">
          <h1 className="header-title">Sybol Compliance Engine</h1>
          <p className="header-sublabel">IEU Labs</p>
        </div>
        <div className={`header-status header-status--${apiStatus}`} aria-live="polite">
          <span className="header-status-dot" aria-hidden="true" />
          <span>{statusLabel}</span>
        </div>
      </div>
    </header>
  );
}
