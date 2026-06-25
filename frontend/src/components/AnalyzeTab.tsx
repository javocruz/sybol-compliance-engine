import { useEffect, useState } from 'react';
import { analyzeImage, ApiError } from '../api/client';
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
        <section className="analyze-tab-upload card">
          <h2 className="analyze-tab-heading">Upload Image</h2>
          <ImageUploader onFileSelect={handleFileSelect} disabled={loading} />
          {previewUrl && file && (
            <ImagePreview file={file} previewUrl={previewUrl} />
          )}
          <button
            type="button"
            className="btn btn-primary analyze-tab-submit"
            onClick={handleAnalyze}
            disabled={!file || loading}
          >
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
          {loading && <LoadingPanel />}
          {error && <ErrorAlert message={error} />}
        </section>

        <section className="analyze-tab-results card">
          <h2 className="analyze-tab-heading">Results</h2>
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
