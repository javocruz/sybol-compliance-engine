# research/regulations/ — Maxim

This folder holds the five regulation PDFs that feed the RAG pipeline.
Files must use these exact stems (`.pdf`):

| File | Source document |
|------|-----------------|
| `eu_ai_act.pdf` | EU AI Act (Regulation 2024/1689) |
| `gdpr.pdf` | GDPR (Regulation 2016/679) |
| `codigo_penal.pdf` | Código Penal (LO 10/1995) |
| `lopdgdd.pdf` | LOPDGDD (LO 3/2018) |
| `ley_13_2022.pdf` | Ley 13/2022 (Comunicación Audiovisual) |

These must be complete, correctly versioned official documents — not
summaries or excerpts. Alex's RAG pipeline ingests directly from this folder.

Once the pipeline is running, validate RAG output for legal accuracy:
cross-check article citations and flag hallucinations or misattributions.
