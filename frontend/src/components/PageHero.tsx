import type { ReactNode } from 'react';
import type { TabId } from './TabNav';
import './PageHero.css';

const HERO_COPY: Record<
  TabId,
  { chip: string; title: ReactNode; lead: string }
> = {
  analyze: {
    chip: 'Media authenticity',
    title: (
      <>
        Score images with <strong>four signal layers</strong>
      </>
    ),
    lead:
      'Upload media to measure metadata, artifacts, visual CNN, and provenance — mapped to EU compliance bands.',
  },
  query: {
    chip: 'Regulation RAG',
    title: (
      <>
        Ask questions about <strong>EU & Spanish law</strong>
      </>
    ),
    lead:
      'Retrieval-augmented answers from ingested AI Act, GDPR, and national regulations with cited articles.',
  },
  issue: {
    chip: 'Verifiable credentials',
    title: (
      <>
        Issue <strong>Sybol-signed</strong> compliance VCs
      </>
    ),
    lead:
      'Analyze media, attach regulation refs, write an audit record, and issue a W3C credential via Sybol wallet.',
  },
  status: {
    chip: 'System',
    title: (
      <>
        Stack health & <strong>readiness</strong>
      </>
    ),
    lead: 'Live status for Qdrant, scoring model, RAG index, and Sybol signing configuration.',
  },
};

interface PageHeroProps {
  activeTab: TabId;
}

export function PageHero({ activeTab }: PageHeroProps) {
  const copy = HERO_COPY[activeTab];
  return (
    <section className="page-hero">
      <span className="sybol-chip sybol-chip--dark">{copy.chip}</span>
      <h2 className="sybol-display-title">{copy.title}</h2>
      <p className="sybol-section-lead">{copy.lead}</p>
    </section>
  );
}
