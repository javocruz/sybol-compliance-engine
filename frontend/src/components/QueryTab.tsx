import { useEffect, useState } from 'react';
import { queryRegulations, ApiError } from '../api/client';
import type { LlmProvider, QueryResponse } from '../types/api';
import { LoadingPanel } from './LoadingPanel';
import { ErrorAlert } from './ErrorAlert';
import { RegulationRefs } from './RegulationRefs';
import './QueryTab.css';

const EXAMPLE_QUESTIONS = [
  'What GDPR requirements apply to processing personal data in images?',
  'What are AI transparency obligations under the EU AI Act?',
  'What Spanish law applies to deepfakes or manipulated media?',
];

const MIN_QUESTION_LENGTH = 10;
const LLM_STORAGE_KEY = 'sybol-query-llm-provider';

function loadStoredProvider(): LlmProvider {
  try {
    const stored = localStorage.getItem(LLM_STORAGE_KEY);
    if (stored === 'mistral' || stored === 'ollama') return stored;
  } catch {
    // localStorage unavailable
  }
  return 'mistral';
}

export function QueryTab() {
  const [question, setQuestion] = useState('');
  const [llmProvider, setLlmProvider] = useState<LlmProvider>(loadStoredProvider);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<QueryResponse | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(LLM_STORAGE_KEY, llmProvider);
    } catch {
      // ignore
    }
  }, [llmProvider]);

  const trimmed = question.trim();
  const canSubmit = trimmed.length >= MIN_QUESTION_LENGTH && !loading;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const response = await queryRegulations(trimmed, llmProvider);
      setResults(response);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 503) {
          const base =
            'The regulation index is not available. Ensure Qdrant is running and the regulations have been ingested (see project README).';
          setError(
            llmProvider === 'ollama'
              ? `${base} If using Ollama, also ensure it is running (\`ollama serve\`) and the model is pulled (\`ollama pull qwen2.5:7b-instruct\`).`
              : base,
          );
        } else if (
          llmProvider === 'ollama' &&
          err.message.toLowerCase().includes('ollama')
        ) {
          setError(
            `${err.message} Ensure Ollama is running: \`ollama serve\` and model is pulled: \`ollama pull qwen2.5:7b-instruct\`.`,
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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void handleSubmit();
    }
  };

  const handleExampleClick = (example: string) => {
    setQuestion(example);
    setError(null);
    setResults(null);
  };

  return (
    <div className="query-tab">
      <div className="query-tab-grid">
        <section className="query-tab-input card card--accent">
          <h2 className="query-tab-heading">Ask a regulation question</h2>
          <p className="query-tab-intro">
            Query EU and Spanish regulations via RAG. Answers are synthesized from
            ingested legal texts with cited articles.
          </p>

          <fieldset className="query-tab-llm-toggle">
            <legend className="query-tab-label">Synthesis model</legend>
            <div className="query-tab-llm-options">
              <button
                type="button"
                className={`query-tab-llm-option${llmProvider === 'mistral' ? ' query-tab-llm-option--active' : ''}`}
                onClick={() => setLlmProvider('mistral')}
                disabled={loading}
                aria-pressed={llmProvider === 'mistral'}
              >
                <span className="query-tab-llm-option-label">Mistral (cloud)</span>
                <span className="query-tab-llm-option-hint">Requires MISTRAL_API_KEY</span>
              </button>
              <button
                type="button"
                className={`query-tab-llm-option${llmProvider === 'ollama' ? ' query-tab-llm-option--active' : ''}`}
                onClick={() => setLlmProvider('ollama')}
                disabled={loading}
                aria-pressed={llmProvider === 'ollama'}
              >
                <span className="query-tab-llm-option-label">Qwen local (Ollama)</span>
                <span className="query-tab-llm-option-hint">qwen2.5:7b-instruct</span>
              </button>
            </div>
          </fieldset>

          <label htmlFor="query-question" className="query-tab-label">
            Your question
          </label>
          <textarea
            id="query-question"
            className="query-tab-textarea"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. What labeling requirements apply to AI-generated content?"
            rows={5}
            disabled={loading}
          />
          <p className="query-tab-hint">
            {trimmed.length < MIN_QUESTION_LENGTH
              ? `Enter at least ${MIN_QUESTION_LENGTH} characters (${trimmed.length}/${MIN_QUESTION_LENGTH})`
              : 'Press ⌘/Ctrl + Enter to submit'}
          </p>

          <div className="query-tab-examples">
            <span className="query-tab-examples-label">Try an example:</span>
            <div className="query-tab-example-chips">
              {EXAMPLE_QUESTIONS.map((example) => (
                <button
                  key={example}
                  type="button"
                  className="query-tab-example-chip"
                  onClick={() => handleExampleClick(example)}
                  disabled={loading}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            className="btn btn-primary query-tab-submit"
            onClick={() => void handleSubmit()}
            disabled={!canSubmit}
          >
            {loading ? 'Searching…' : 'Search regulations'}
          </button>

          {loading && (
            <LoadingPanel
              title="Searching regulations…"
              hint={
                llmProvider === 'ollama'
                  ? 'Local Ollama synthesis may take longer on CPU.'
                  : 'Retrieval and synthesis may take a few seconds.'
              }
            />
          )}
          {error && <ErrorAlert title="Query failed" message={error} />}
        </section>

        <section className="query-tab-results card">
          <div className="query-tab-results-header">
            <h2 className="query-tab-heading">Answer</h2>
            {results && (
              <span className="query-tab-model-badge" title={results.llm_provider}>
                Powered by {results.llm_model}
              </span>
            )}
          </div>
          {results ? (
            <div className="query-tab-answer-block">
              <div className="query-tab-answer">
                {results.answer.split('\n').map((paragraph, i) =>
                  paragraph.trim() ? (
                    <p key={i}>{paragraph}</p>
                  ) : null,
                )}
              </div>

              <h3 className="query-tab-refs-heading">
                Regulation citations
                <span className="query-tab-refs-count">
                  ({results.regulation_refs.length})
                </span>
              </h3>
              <RegulationRefs refs={results.regulation_refs} />
            </div>
          ) : (
            <p className="query-tab-placeholder">
              Submit a question to see an AI-synthesized answer with regulation
              citations.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
