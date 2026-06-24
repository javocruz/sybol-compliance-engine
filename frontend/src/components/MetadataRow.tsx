import { useState } from 'react';
import './MetadataRow.css';

interface MetadataRowProps {
  mediaHash: string;
  modelVersion: string;
  analysisTimestamp: string;
}

function truncateHash(hash: string, visible = 8): string {
  if (hash.length <= visible * 2 + 3) return hash;
  return `${hash.slice(0, visible)}…${hash.slice(-visible)}`;
}

export function MetadataRow({ mediaHash, modelVersion, analysisTimestamp }: MetadataRowProps) {
  const [copied, setCopied] = useState(false);

  const copyHash = async () => {
    try {
      await navigator.clipboard.writeText(mediaHash);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <dl className="metadata-row">
      <div className="metadata-item">
        <dt>Media hash</dt>
        <dd>
          <code className="metadata-hash" title={mediaHash}>
            {truncateHash(mediaHash)}
          </code>
          <button type="button" className="btn btn-secondary metadata-copy" onClick={copyHash}>
            {copied ? 'Copied' : 'Copy'}
          </button>
        </dd>
      </div>
      <div className="metadata-item">
        <dt>Model version</dt>
        <dd>{modelVersion}</dd>
      </div>
      <div className="metadata-item">
        <dt>Analysis time</dt>
        <dd>{new Date(analysisTimestamp).toLocaleString()}</dd>
      </div>
    </dl>
  );
}
