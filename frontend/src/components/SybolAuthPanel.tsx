import { useCallback, useEffect, useState } from 'react';
import { authLogin, authLogout, authStatus, ApiError } from '../api/client';
import type { AuthStatusResponse } from '../types/api';
import { ErrorAlert } from './ErrorAlert';
import './SybolAuthPanel.css';

export function SybolAuthPanel() {
  const [status, setStatus] = useState<AuthStatusResponse | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    setLoading(true);
    try {
      const next = await authStatus();
      setStatus(next);
      if (next.email && !email) {
        setEmail(next.email);
      }
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, [email]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await authLogin(email.trim(), password);
      setPassword('');
      await refreshStatus();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Login failed — could not reach the API.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const next = await authLogout();
      setStatus(next);
      setPassword('');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Logout failed — could not reach the API.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const sessionActive = status?.session_active ?? false;
  const authenticated = status?.authenticated ?? false;

  return (
    <section className="sybol-auth card" aria-labelledby="sybol-auth-heading">
      <h2 id="sybol-auth-heading" className="sybol-auth-heading">
        Sybol sign-in
      </h2>
      <p className="sybol-auth-intro">
        Sign in with your Sybol wallet Cognito email and password.
      </p>

      {loading ? (
        <p className="sybol-auth-muted">Checking sign-in status…</p>
      ) : sessionActive ? (
        <div className="sybol-auth-signed-in">
          <p className="sybol-auth-status-line">
            <span className="sybol-auth-status-dot sybol-auth-status-dot--ok" aria-hidden />
            Signed in as <strong>{status?.email ?? 'wallet user'}</strong>
          </p>
          <button
            type="button"
            className="btn btn-secondary sybol-auth-logout"
            onClick={() => void handleLogout()}
            disabled={submitting}
          >
            {submitting ? 'Signing out…' : 'Sign out'}
          </button>
        </div>
      ) : authenticated ? (
        <p className="sybol-auth-muted">
          Enter your login.
        </p>
      ) : null}

      {!sessionActive && (
        <form className="sybol-auth-form" onSubmit={(e) => void handleLogin(e)}>
          <label className="sybol-auth-label">
            Email
            <input
              className="sybol-auth-input"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
              required
            />
          </label>
          <label className="sybol-auth-label">
            Password
            <input
              className="sybol-auth-input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={submitting}
              required
            />
          </label>
          <button
            type="submit"
            className="btn btn-primary sybol-auth-submit"
            disabled={submitting || !email.trim() || !password}
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      )}

      {status && !status.catalog_configured && (
        <p className="sybol-auth-hint">
          Catalog IDs are still required in <code>src/.env</code> (
          <code>SYBOL_DOCUMENT_ID</code>, <code>SYBOL_ISSUER_KEY</code>,{' '}
          <code>SYBOL_RECIPIENT_DID</code>).
        </p>
      )}

      {error && <ErrorAlert title="Sign-in failed" message={error} />}
    </section>
  );
}
