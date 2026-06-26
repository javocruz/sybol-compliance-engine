import { useEffect, useState } from 'react';
import { analyzeImage, fetchSystemStatus, ApiError } from '../api/client';
import type { AnalyzeResponse } from '../types/api';
import { ImageUploader, isAcceptedImageType } from './ImageUploader';
import { ImagePreview } from './ImagePreview';
import { LoadingPanel } from './LoadingPanel';
import { ErrorAlert } from './ErrorAlert';
import { ResultsPanel } from './ResultsPanel';
import './AnalyzeTab.css';

export function AnalyzeTab() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<AnalyzeResponse | null>(null);
  const [modelReady, setModelReady] = useState(true);

  useEffect(() => {
    void fetchSystemStatus()
      .then((data) => setModelReady(data.model_loaded))
      .catch(() => setModelReady(true));
  }, []);

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

  const handleAnalyze = async () => {
    if (!file || loading) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const response = await analyzeImage(file);
      setResults(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
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
    <div className="analyze-tab">
      <div className="analyze-tab-grid">
        <section className="sybol-card-service">
          <h3 className="sybol-card-heading">Upload image</h3>
          <p className="sybol-card-intro">
            JPEG, PNG, or WebP — scored against metadata, artifacts, visual CNN, and provenance.
          </p>
          <div className="analyze-tab-demo-tips">
            <strong>Demo expectations:</strong>
            <ul>
              <li>Authentic camera JPEG (EXIF intact) → ~0.8+, compliant</li>
              <li>AI-generated PNG → ~0.26 cap, non-compliant</li>
              <li>Edited / re-saved JPEG → ~0.35–0.6, review</li>
            </ul>
          </div>
          <ImageUploader onFileSelect={handleFileSelect} disabled={loading} />
          {previewUrl && file && (
            <ImagePreview file={file} previewUrl={previewUrl} />
          )}
          <button
            type="button"
            className="btn-solid analyze-tab-submit"
            onClick={handleAnalyze}
            disabled={!file || loading}
          >
            {loading ? 'Analyzing…' : 'Analyze authenticity'}
          </button>
          {loading && (
            <LoadingPanel
              title="Analyzing image…"
              hint={
                modelReady
                  ? 'Scoring metadata, artifacts, visual signals, and provenance.'
                  : 'Loading scoring model — first request after restart may take longer.'
              }
            />
          )}
          {error && <ErrorAlert message={error} />}
        </section>

        <section className="sybol-card-white">
          <h3 className="sybol-card-heading">Results</h3>
          {results ? (
            <ResultsPanel results={results} />
          ) : (
            <p className="analyze-tab-placeholder">
              Upload an image and run analysis to see compliance results.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
