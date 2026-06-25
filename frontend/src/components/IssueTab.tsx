import { useEffect, useState } from 'react';
import { issueCredential, ApiError } from '../api/client';
import type { IssueResponse } from '../types/api';
import { ImageUploader, isAcceptedImageType } from './ImageUploader';
import { ImagePreview } from './ImagePreview';
import { LoadingPanel } from './LoadingPanel';
import { ErrorAlert } from './ErrorAlert';
import { CredentialResultsPanel } from './CredentialResultsPanel';
import './IssueTab.css';

export function IssueTab() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<IssueResponse | null>(null);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const handleFileSelect = (selected: File) => {
    if (!isAcceptedImageType(selected.type)) {
      setError('Please choose a JPEG, PNG, or WebP image.');
      return;
    }
    setFile(selected);
    setError(null);
    setResults(null);
  };

  const handleIssue = async () => {
    if (!file || loading) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const response = await issueCredential(file);
      setResults(response);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 503 && err.message.includes('Sybol signing is not configured')) {
          setError(
            `${err.message} Configure Sybol credentials in src/.env (see src/.env.example).`,
          );
        } else if (err.status === 503) {
          setError(
            `${err.message} Ensure Qdrant is running and regulations are ingested (see project README).`,
          );
        } else {
          setError(err.message);
        }
      } else if (err instanceof TypeError) {
        setError('Network error — could not reach the API. Is the server running?');
      } else {
        setError('An unexpected error occurred.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="issue-tab">
      <div className="issue-tab-grid">
        <section className="issue-tab-upload card card--accent">
          <h2 className="issue-tab-heading">Issue credential</h2>
          <p className="issue-tab-intro">
            Upload media to score authenticity, query applicable regulations, write an
            audit record, and issue a signed W3C Verifiable Credential via Sybol.
          </p>
          <ImageUploader onFileSelect={handleFileSelect} disabled={loading} />
          {previewUrl && file && (
            <ImagePreview file={file} previewUrl={previewUrl} />
          )}
          <button
            type="button"
            className="btn btn-primary issue-tab-submit"
            onClick={() => void handleIssue()}
            disabled={!file || loading}
          >
            {loading ? 'Issuing…' : 'Issue credential'}
          </button>
          {loading && (
            <LoadingPanel
              title="Issuing credential…"
              hint="Scoring, regulation lookup, audit write, and Sybol signing may take 30–60s on first run."
            />
          )}
          {error && <ErrorAlert title="Issuance failed" message={error} />}
        </section>

        <section className="issue-tab-results card">
          <h2 className="issue-tab-heading">Credential</h2>
          {results ? (
            <CredentialResultsPanel results={results} />
          ) : (
            <p className="issue-tab-placeholder">
              Upload an image and issue a credential to see the signed VC details.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
