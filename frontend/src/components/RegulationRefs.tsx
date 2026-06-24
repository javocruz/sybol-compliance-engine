import type { RegulationRef } from '../types/api';
import { resolveRegulationUrl } from '../utils/regulationUrl';
import './RegulationRefs.css';

interface RegulationRefsProps {
  refs: RegulationRef[];
}

export function RegulationRefs({ refs }: RegulationRefsProps) {
  if (refs.length === 0) {
    return (
      <p className="regulation-refs-empty">
        No regulation citations were returned for this query.
      </p>
    );
  }

  return (
    <ul className="regulation-refs">
      {refs.map((ref, index) => {
        const href = ref.url ? resolveRegulationUrl(ref.url) : null;

        return (
        <li key={`${ref.regulation}-${ref.article}-${index}`} className="regulation-ref">
          <div className="regulation-ref-header">
            <span className="regulation-ref-name">{ref.regulation}</span>
            <span className="regulation-ref-article">Article {ref.article}</span>
          </div>
          {href ? (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="regulation-ref-link"
            >
              View source
            </a>
          ) : (
            <span className="regulation-ref-no-link">Source link unavailable</span>
          )}
        </li>
        );
      })}
    </ul>
  );
}
