expl# Sybol Compliance Engine — System Architecture

**Project:** Sybol × IEU Labs — Compliance AI Engine  
**Team lead:** Javier Cruz  
**Partner:** Sybol — Iñigo García de Mata (CTO)  
**Last updated:** June 2026

This document describes the technical architecture of the Compliance AI Engine for paper Chapter 4 (System Design) and demo preparation. It reflects the repository as deployed on Railway with FastAPI, Qdrant, and Sybol's digital identity infrastructure.

---

## 1. Problem and design goal

There is no standardized, machine-readable way to prove whether a piece of media is authentic and which EU regulations apply to it. The Compliance AI Engine closes that gap by connecting three capabilities into a single pipeline:

1. **Media authenticity scoring** — four independent signals combined into a compliance score.
2. **Regulatory retrieval (RAG)** — EU regulation articles that explain and justify the result.
3. **Verifiable Credential issuance** — a cryptographically signed W3C VC issued through Sybol.

Every output is **explainable** (per-signal breakdown + regulation citations) and **verifiable** (signed credential, audit trail, media hash — no raw image storage).

---

## 2. High-level architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Client (demo / API consumer)                        │
└─────────────────────────────────────────────────────────────────────────────┘
         │ POST image                    │ POST question              │ POST image
         ▼                               ▼                            ▼
┌─────────────────┐              ┌─────────────────┐         ┌──────────────────────┐
│  /api/analyze   │              │  /api/query     │         │  /api/issue          │
│  (scoring only) │              │  (RAG only)     │         │  (full pipeline)     │
└────────┬────────┘              └────────┬────────┘         └──────────┬───────────┘
         │                               │                              │
         ▼                               ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FastAPI application (src/api/)                           │
│  main.py · routes/analyze.py · routes/query.py · routes/issue.py          │
│  dependencies.py · schemas.py                                               │
└─────────────────────────────────────────────────────────────────────────────┘
         │                               │                              │
         ▼                               ▼                              ▼
┌─────────────────┐              ┌─────────────────┐         ┌──────────────────────┐
│  Scoring Module │              │  RAG Engine     │         │  Credentials Module  │
│  src/scoring/   │──────────────│  src/rag/       │────────▶│  src/credentials/    │
│  m, a, v, p     │              │  LlamaIndex     │         │  vc_builder · audit  │
└─────────────────┘              │  + Mistral      │         │  sybol_client        │
                                   └────────┬────────┘         └──────────┬───────────┘
                                            │                              │
                                            ▼                              ▼
                                   ┌─────────────────┐         ┌──────────────────────┐
                                   │  Qdrant         │         │  Sybol businessLogic │
                                   │  regulations    │         │  API (signed VC)     │
                                   │  media_audit    │         │  api.sybol.io        │
                                   └─────────────────┘         └──────────────────────┘
```

### End-to-end flow (`POST /api/issue`)

When a client uploads an image to `/api/issue`, the system runs the full pipeline:

1. **Score** — preprocess image, extract four signals, compute weighted authenticity score and compliance status.
2. **Retrieve** — query the RAG engine with the score and status; retrieve top-k regulation chunks from Qdrant; synthesize answer with Mistral Large.
3. **Audit** — write a metadata-only record to Qdrant `media_audit` (hash, scores, refs — no image bytes).
4. **Build** — construct an unsigned W3C VC 1.1 payload (`MediaComplianceCredential`).
5. **Sign** — submit payload to Sybol `businessLogic` API; return signed VC with `issuer`, `proof`, and `credentialStatus`.

`/api/analyze` runs only step 1. `/api/query` runs only the RAG retrieval step (requires a natural-language question).

---

## 3. Technology stack

| Layer | Technology | Role |
|-------|------------|------|
| API | FastAPI + Uvicorn | HTTP endpoints, OpenAPI docs, dependency injection |
| Scoring — deepfake | `dima806/deepfake_vs_real_image_detection` (HuggingFace) | CNN artifact signal |
| Scoring — vision | OpenCV (`opencv-python-headless`) | Lighting, shadow, edge consistency |
| Scoring — metadata | ExifRead | EXIF integrity checks |
| Scoring — provenance | imagehash (pHash) | Perceptual hash vs reference index |
| RAG framework | LlamaIndex | Document ingest, chunking, retrieval |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding (no external API) |
| Vector database | Qdrant | Regulation index + audit trail |
| LLM synthesis | Mistral Large (`mistral-large-latest`) | Regulation answer synthesis |
| Credentials | W3C VC Data Model 1.1 | Unsigned payload shape |
| Signing | Sybol businessLogic API | DID + svault cryptographic signing |
| Auth | AWS Cognito (access + ID tokens) | Tenant-scoped API authentication |
| Deployment | Railway + Docker | Containerised FastAPI, separate Qdrant service |
| CI | GitHub Actions | Lint, format, mypy, pytest (~90% coverage) |
| Package management | Poetry | Dependencies and dev tooling |

---

## 4. Component design

### 4.1 Media scoring module (`src/scoring/`)

The scoring module evaluates image authenticity through four independent signals. Each signal produces a sub-score in `[0.0, 1.0]`. They are combined into a feature vector **X = [m, a, v, p]** and fed into a weighted scoring function.

| Signal | Code | What it measures | Techniques |
|--------|------|------------------|------------|
| **m** — Metadata | `metadata.py` | EXIF integrity, editing software tags, timestamp anomalies | ExifRead; flags Photoshop, GIMP, Stable Diffusion, etc. |
| **a** — Artifacts | `detector.py`, `artifacts.py` | AI-generated or synthetic patterns | CNN deepfake detector, FFT frequency analysis, noise residual |
| **v** — Visual | `visual.py` | Lighting uniformity, shadow direction, edge blending | OpenCV — **facial landmarks explicitly excluded** (GDPR Art. 4(14), AI Act Art. 5) |
| **p** — Provenance | `provenance.py` | Match against known authentic reference set | Perceptual hash (pHash); no third-party reverse lookup |

**Preprocessing** (`preprocess.py`): resize to 224×224, convert to RGB, strip EXIF before transform, compute SHA-256 `media_hash` of raw bytes before resize.

**Scoring function** (`scorer.py`):

```
S = wm·m + wa·a + wv·v + wp·p    (weights: 0.30, 0.30, 0.20, 0.20)
```

Platt scaling calibration is scaffolded but not yet enabled (`PLATT_ENABLED = False`).

**Compliance status mapping:**

| Score range | Status | Interpretation |
|-------------|--------|----------------|
| 0.0 – 0.3 | `non-compliant` | Likely AI-generated or deepfake |
| 0.3 – 0.7 | `review` | Partially authentic or edited — human review (GDPR Art. 22) |
| 0.7 – 1.0 | `compliant` | Passes signal checks |

**Key files:** `pipeline.py` (orchestration), `constants.py` (weights, thresholds), `models.py` (data types).

---

### 4.2 RAG compliance engine (`src/rag/`)

The RAG engine ingests EU regulation PDFs and retrieves article-level citations that justify the compliance score.

**Regulation sources (five PDFs):**

- EU AI Act — synthetic content transparency (Art. 50), prohibited practices (Art. 5)
- GDPR — data minimisation, automated decision-making (Art. 22), biometric data (Art. 4(14))
- ESPR / Digital Product Passport (EU 2024/1781)
- LOPDGDD — Spanish GDPR implementation
- Ley 13/2022 — Spanish audiovisual law

**Pipeline stages:**

| Stage | Module | Detail |
|-------|--------|--------|
| Load | `ingest.py` | `SimpleDirectoryReader` from `research/regulations/` |
| Chunk | `ingest.py` | `SentenceSplitter`, 400–600 tokens with overlap; metadata: regulation name, article, section |
| Embed | `embeder.py` | `all-MiniLM-L6-v2` locally — no external embedding API (GDPR-safe) |
| Index | `indexer.py` | Qdrant collection `regulations`, filterable metadata |
| Query | `query.py` | Embed query → similarity search (top-k = 5) → Mistral synthesis |
| Guard | `query.py` | Drops citations with `Unknown` regulation or article (hallucination filter) |

**Output:** `ComplianceResult` with `summary` (natural-language answer) and `regulationRefs` (structured array: regulation, article, URL).

**One-off ingest:** `PYTHONPATH=src poetry run python -m scripts.ingest` — chunks PDFs, embeds, writes to Qdrant. API startup calls `load_index()` to attach to the existing collection; it does not re-ingest automatically.

---

### 4.3 Credentials module (`src/credentials/`)

Encodes scoring and regulatory results into a W3C Verifiable Credential and submits it to Sybol for signing.

| Component | File | Responsibility |
|-----------|------|----------------|
| VC builder | `vc_builder.py` | Builds unsigned W3C VC 1.1 payload (`MediaComplianceCredential`) |
| Audit trail | `audit.py` | Writes metadata-only record to Qdrant `media_audit`; returns `evidenceUrl` |
| Sybol client | `sybol_client.py` | `POST` to Sybol businessLogic API; Cognito Bearer + `x-id-token` auth |

**Unsigned VC payload fields:**

| Field | Source |
|-------|--------|
| `@context` | `https://www.w3.org/2018/credentials/v1` |
| `id` | `urn:uuid:{uuid}` |
| `type` | `VerifiableCredential`, `MediaComplianceCredential` |
| `issuanceDate` | UTC ISO 8601 timestamp |
| `credentialSubject.mediaHash` | SHA-256 of original file |
| `credentialSubject.authenticityScore` | Weighted score S |
| `credentialSubject.scoreBreakdown` | `{m, a, v, p}` |
| `credentialSubject.complianceStatus` | `compliant` / `non-compliant` / `review` |
| `credentialSubject.modelVersion` | Deepfake model identifier |
| `credentialSubject.analysisTimestamp` | UTC ISO 8601 |
| `credentialSubject.regulationRefs` | `[{regulation, article, url}]` |
| `credentialSubject.evidenceUrl` | Qdrant audit record URL |

**Intentionally absent from unsigned payload** (added by Sybol on signing):

- `issuer` — resolved server-side from authenticated tenant context
- `proof` — cryptographic signature (DataIntegrityProof)
- `credentialStatus` — StatusList2021 revocation entry

**GDPR data minimisation:** raw image bytes are never stored. Only the hash, feature signals, and metadata are persisted in the audit trail and credential.

---

### 4.4 API layer (`src/api/`)

| Endpoint | Method | Dependencies | Response |
|----------|--------|--------------|----------|
| `/health` | GET | None | `{"status": "ok"}` |
| `/api/analyze` | POST | Scoring only | Score, breakdown, status, hash, model version |
| `/api/query` | POST | Qdrant index + `MISTRAL_API_KEY` | Answer + `regulationRefs` |
| `/api/issue` | POST | Qdrant + Mistral + Sybol tokens | Signed VC + unsigned payload |

**Startup behaviour:** the app attempts to load the Qdrant regulation index on startup. If Qdrant is unavailable, the server still starts; `/api/analyze` works, but `/api/query` and `/api/issue` return 503 until the index is available.

**Configuration** (`dependencies.py`): all secrets loaded from environment variables via a `Settings` dataclass — Qdrant URL/key/collections, Sybol API URL/tokens, Mistral key.

Interactive API documentation: `http://localhost:8000/docs`

---

## 5. Data stores

### Qdrant — two collections

| Collection | Purpose | Content |
|------------|---------|---------|
| `regulations` | RAG vector index | Embedded regulation chunks with metadata (regulation name, article, section) |
| `media_audit` | Audit trail | Metadata-only analysis records keyed by credential UUID |

The audit collection uses a minimal 1-dimensional vector (metadata store pattern). Points are keyed by credential ID; payload holds scores, breakdown, regulation refs, timestamps.

### Local / reference data

| Path | Purpose |
|------|---------|
| `research/regulations/` | Source PDFs for RAG ingest |
| `qa/test_cases/authentic/` | Reference images for provenance signal (pHash index) |
| `qa/test_cases/golden/` | Golden dataset for acceptance testing (TC-001–003) |

---

## 6. External integrations

### Sybol businessLogic API

- **Endpoint:** `POST https://api.sybol.io/api/bl/credentials`
- **Auth:** `Authorization: Bearer {access_token}` + `x-id-token: {id_token}` (AWS Cognito)
- **Input:** Unsigned VC 1.1 JSON payload from `vc_builder`
- **Output:** Signed VC with `issuer`, `proof`, `credentialStatus`

Login credentials (email/password) are exchanged for Cognito tokens via the AWS Cognito auth flow. Tokens are valid for ~1 hour and must be refreshed for long-running deployments.

### Mistral API

- **Model:** `mistral-large-latest`
- **Use:** Synthesis step in RAG query pipeline only
- **Not used for:** embeddings (local model) or scoring

---

## 7. Deployment architecture

```
┌──────────────────────────────────────────────────────────┐
│  Railway                                                 │
│  ┌─────────────────────┐    ┌─────────────────────────┐  │
│  │  FastAPI service    │    │  Qdrant service         │  │
│  │  Docker (Python     │───▶│  Vector DB              │  │
│  │  3.12 + Poetry)     │    │  regulations + audit    │  │
│  │  PORT from Railway  │    │  persistent volume      │  │
│  │  /health check      │    │                         │  │
│  └──────────┬──────────┘    └─────────────────────────┘  │
└─────────────┼────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│  Sybol API              │    │  Mistral API            │
│  api.sybol.io           │    │  (LLM synthesis)        │
│  Cognito auth           │    │                         │
└─────────────────────────┘    └─────────────────────────┘
```

- **Container:** multi-stage Dockerfile, `uvicorn src.api.main:app`
- **Health check:** `GET /health` — Railway uses this for deploy success
- **CI:** GitHub Actions on `main` — ruff, black, mypy, pytest with coverage gate
- **Secrets:** environment variables on Railway (never committed to repo)

---

## 8. Security and compliance design choices

| Concern | Design decision |
|---------|-----------------|
| GDPR data minimisation | No raw images stored; only hash + feature signals in audit trail and VC |
| Biometric data (Art. 4(14)) | Facial landmark detection explicitly excluded from visual signal |
| Automated decisions (Art. 22) | `review` band (0.3–0.7) requires human-in-the-loop; no automated rejection |
| Embedding privacy | Local `sentence-transformers` model — regulation text never sent to external embedding APIs |
| Provenance privacy | pHash vs local reference index only — no third-party reverse image lookup |
| Multi-tenancy | Sybol resolves issuer DID from Cognito `custom:tenant_id` in ID token |
| Credential revocation | StatusList2021 entry added by Sybol on signing |
| Auditability | Every issuance writes a Qdrant audit record linked via `evidenceUrl` |

---

## 9. Repository structure

```
sybol-compliance-engine/
├── Architecture.md          ← this document
├── src/
│   ├── api/                 # FastAPI app, routes, schemas, dependencies
│   │   └── routes/
│   │       ├── analyze.py   # POST /api/analyze
│   │       ├── query.py     # POST /api/query
│   │       └── issue.py     # POST /api/issue
│   ├── scoring/             # Media authenticity pipeline (m, a, v, p)
│   ├── rag/                 # Regulation ingest, index, query
│   ├── credentials/         # VC builder, Sybol client, audit trail
│   └── scripts/
│       ├── ingest.py        # One-off PDF → Qdrant ingest
│       └── export_openapi.py
├── tests/                   # ~93 automated tests, ~90% coverage
│   ├── unit/
│   ├── integration/
│   └── mocks/               # Sybol API mock for CI
├── research/regulations/    # EU regulation PDFs (RAG source)
├── qa/test_cases/           # Golden dataset + acceptance test definitions
├── docs/                    # Project scope, status, team ownership
├── sybol_docs/              # Sybol platform reference documentation
├── Dockerfile
├── railway.toml
└── pyproject.toml
```

---

## 10. Team ownership map

| Component | Primary owner |
|-----------|---------------|
| Scoring pipeline (`src/scoring/`) | Javier Cruz |
| RAG engine (`src/rag/`) | Alex Garcia Perdriau |
| API + deployment | Alex Garcia Perdriau, Darius-Luca Petruti |
| Credentials + Sybol integration | Javier Cruz, Darius-Luca Petruti |
| CI/CD, Railway, Docker | Darius-Luca Petruti |
| QA framework + acceptance tests | Saba Zarandia |
| Golden dataset + RAG evaluation | Youssef Ayman |
| Regulation PDFs + legal validation | Maxim Heller |
| Paper + demo materials | Jana Eltoni |

---

## 11. Current limitations and planned extensions

| Area | Current state | Planned |
|------|---------------|---------|
| VC standard | W3C VC Data Model 1.1 payload | VC 2.0 fields (`validFrom`, updated `@context`) when Sybol catalog confirms |
| Score calibration | Hand-tuned weights; Platt scaling disabled | Calibrate on golden dataset |
| Provenance signal | Defaults to 0.5 when reference folder empty | Populate `qa/test_cases/authentic/` |
| RAG evaluation | No automated precision/recall metrics | ragas/deepeval harness (Youssef) |
| Acceptance testing | TC-006 automated; TC-001–003 harness ready | Execute once golden dataset lands |

---

## References

- [README.md](./README.md) — setup and run instructions
- [docs/PROJECT_STATUS.md](./docs/PROJECT_STATUS.md) — component status and blockers
- [docs/AI Lab Summer Work.md](./docs/AI%20Lab%20Summer%20Work.md) — full project scope
- [src/credentials/README_Darius.md](./src/credentials/README_Darius.md) — Sybol integration notes
- [sybol_docs/global/api/authentication.md](./sybol_docs/global/api/authentication.md) — Cognito auth flow

---

*Maintained by Javier Cruz (technical lead). Update when a major architectural change is merged.*
