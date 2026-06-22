# Local Testing Guide

Complete guide for running and validating the Compliance Engine **on your machine**. This document intentionally **does not** cover Railway deployment — see [RAILWAY_SETUP.md](./RAILWAY_SETUP.md) for that.

**Remote services used locally:**

| Service | Used for | Required? |
|---------|----------|-----------|
| **Sybol BusinessWallet API** (`api.develop.wallet.sybol.id`) | `/api/issue`, catalog discovery, signing | Only for full VC issuance |
| **Mistral API** | `/api/query`, RAG step inside `/api/issue` | Only for RAG endpoints |

Everything else (FastAPI, Qdrant, embeddings, deepfake model, pytest) runs locally.

---

## Table of contents

1. [Architecture at a glance](#1-architecture-at-a-glance)
2. [Prerequisites](#2-prerequisites)
3. [One-time setup](#3-one-time-setup)
4. [Environment variables](#4-environment-variables)
5. [Load env vars before every session](#5-load-env-vars-before-every-session)
6. [Tier 0 — Health and automated tests](#6-tier-0--health-and-automated-tests)
7. [Tier 1 — Scoring only (`/api/analyze`)](#7-tier-1--scoring-only-apianalyze)
8. [Tier 2 — Golden dataset regression (TC-001–003)](#8-tier-2--golden-dataset-regression-tc-001003)
9. [Tier 3 — RAG pipeline (`/api/query`)](#9-tier-3--rag-pipeline-apiquery)
10. [Tier 4 — VC payload without Sybol (mocked)](#10-tier-4--vc-payload-without-sybol-mocked)
11. [Tier 5 — Full issuance (`/api/issue` + Sybol)](#11-tier-5--full-issuance-apiissue--sybol)
12. [Readiness checklist script](#12-readiness-checklist-script)
13. [Troubleshooting](#13-troubleshooting)
14. [Quick reference matrix](#14-quick-reference-matrix)

---

## 1. Architecture at a glance

```
┌─────────────────────────────────────────────────────────────────┐
│  Your laptop                                                    │
│                                                                 │
│  FastAPI (:8000)                                                │
│    ├── /health          → no deps                               │
│    ├── /api/analyze     → scoring (local HF model + OpenCV)     │
│    ├── /api/query       → Qdrant (local Docker) + Mistral (cloud)│
│    └── /api/issue       → above + Qdrant audit + Sybol (cloud)  │
│                                                                 │
│  Qdrant (:6333)         → Docker container                      │
│  pytest                 → mocks Qdrant/Mistral/Sybol in unit tests│
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   Mistral API                    Sybol Wallet API
   (console.mistral.ai)           (api.develop.wallet.sybol.id)
```

Test in order: **Tier 0 → 1 → 2 → 3 → 4 → 5**. Each tier adds dependencies; do not skip troubleshooting at an earlier tier.

---

## 2. Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10 – 3.13 | Runtime |
| Poetry | latest | Dependency management (recommended) |
| Docker | any recent | Local Qdrant |
| `curl` | any | Manual API smoke tests |

**Disk / network (first run):**

- Deepfake model download from HuggingFace (~100 MB) on first scoring request
- Embedding model `sentence-transformers/all-MiniLM-L6-v2` on first RAG ingest (~90 MB)

---

## 3. One-time setup

From the **repository root**:

```bash
# Install Python dependencies (includes pytest, ruff, etc.)
poetry install --with dev

# Local secrets file (never commit src/.env)
cp src/.env.example src/.env
```

Edit `src/.env` — minimum for local scoring-only work:

```env
QDRANT_URL=http://localhost:6333
```

Add when you test RAG:

```env
MISTRAL_API_KEY=<your-mistral-key>
```

Add when you test `/api/issue` (see [§11](#11-tier-5--full-issuance-apiissue--sybol)):

```env
SYBOL_API_BASE_URL=https://api.develop.wallet.sybol.id
SYBOL_ACCESS_TOKEN=...
SYBOL_ID_TOKEN=...
SYBOL_DOCUMENT_ID=...
SYBOL_ISSUER_KEY=...
```

---

## 4. Environment variables

Copy template: `src/.env.example` → `src/.env`.

| Variable | Tier | Default | Notes |
|----------|------|---------|-------|
| `QDRANT_URL` | 3+ | `http://localhost:6333` | Local Docker Qdrant |
| `QDRANT_API_KEY` | 3+ | empty | Not needed for default local Qdrant |
| `QDRANT_COLLECTION` | 3+ | `regulations` | RAG index name |
| `QDRANT_AUDIT_COLLECTION` | 5 | `media_audit` | Audit trail for `/api/issue` |
| `MISTRAL_API_KEY` | 3+ | — | Required for live RAG synthesis |
| `SYBOL_API_BASE_URL` | 5 | `https://api.develop.wallet.sybol.id` | Sybol develop API |
| `SYBOL_ACCESS_TOKEN` | 5 | — | Cognito access JWT |
| `SYBOL_ID_TOKEN` | 5 | — | Cognito ID JWT (`custom:tenant_id`) |
| `SYBOL_EMAIL` / `SYBOL_PASSWORD` | 5 | — | Optional; `SybolClient` tries `/auth/login` (see §11) |
| `SYBOL_DOCUMENT_ID` | 5 | — | Catalog document UUID for MediaCompliance |
| `SYBOL_ISSUER_KEY` | 5 | — | KMS / issuer key id from Sybol |
| `SYBOL_SUBJECT_DID` | 5 | optional | Subject DID if required by catalog |
| `SYBOL_LEVEL_OF_ASSURANCE` | 5 | `2` | Catalog issuance LOA |
| `SYBOL_REQUEST_TIMEOUT` | 5 | `30.0` | HTTP timeout seconds |

**Test-only override:**

| Variable | Purpose |
|----------|---------|
| `SYBOL_GOLDEN_DATASET` | Override path to golden images (default `qa/test_cases/golden/`) |

---

## 5. Load env vars before every session

The app reads **`os.environ`** — `src/.env` is **not** loaded automatically by uvicorn unless you export it or pass `--env-file`.

**Recommended (every new terminal):**

```bash
set -a && source src/.env && set +a
export PYTHONPATH=src
```

**Alternative (uvicorn built-in):**

```bash
PYTHONPATH=src poetry run uvicorn src.api.main:app --reload \
  --env-file src/.env --host 127.0.0.1 --port 8000
```

Helper scripts `sybol_probe_issue.py` parse `src/.env` themselves; pytest uses mocked env from `tests/conftest.py`.

---

## 6. Tier 0 — Health and automated tests

No Docker, no API keys, no Sybol.

```bash
export PYTHONPATH=src

# Unit tests (mocked Qdrant, Mistral, Sybol)
poetry run pytest tests/unit/ -q

# Integration tests (mostly mocked; golden regression may download model)
poetry run pytest tests/integration/ -q

# Full suite with coverage gate (≥ 80%)
poetry run pytest tests/unit tests/integration --cov=src --cov-fail-under=80
```

**Start API and check health:**

```bash
poetry run uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
curl http://127.0.0.1:8000/health
# → {"status":"ok"}
```

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

**Pass criteria:** all pytest tests green (except known skips), `/health` returns 200.

---

## 7. Tier 1 — Scoring only (`/api/analyze`)

Works **without** Qdrant, Mistral, or Sybol. First request downloads the deepfake model (~15–30 s).

### 7.1 HTTP smoke test

```bash
# Authentic camera JPEG — expect compliant (score ≥ 0.7)
curl -s -X POST http://127.0.0.1:8000/api/analyze \
  -F "file=@qa/test_cases/golden/authentic/ar_1.JPG" | python3 -m json.tool

# AI-generated PNG — expect non-compliant (score ≤ 0.3)
curl -s -X POST http://127.0.0.1:8000/api/analyze \
  -F "file=@qa/test_cases/golden/ai_generated/beach_sd.png" | python3 -m json.tool
```

**Expected response fields:**

| Field | Meaning |
|-------|---------|
| `authenticity_score` | Overall score in `[0.0, 1.0]` |
| `score_breakdown` | `[m, a, v, p]` — metadata, artifacts, visual, provenance |
| `compliance_status` | `compliant` (≥ 0.7), `review` (0.3–0.7), `non-compliant` (< 0.3) |
| `media_hash` | SHA-256 of raw file bytes |

### 7.2 Python (no server)

```bash
PYTHONPATH=src python3 -c "
from pathlib import Path
from scoring.pipeline import score_image

path = Path('qa/test_cases/golden/authentic/ar_1.JPG')
result = score_image(path.read_bytes(), filename=path.name, content_type='image/jpeg')
print(result.model_dump_json(indent=2))
"
```

### 7.3 TC-004 — corrupted file

```bash
curl -s -X POST http://127.0.0.1:8000/api/analyze \
  -F "file=@qa/test_cases/corrupted/not_a_real_image.txt;type=image/jpeg"
# → HTTP 400, clean error message (no server crash)
```

Or run unit tests covering `ScoringError` paths:

```bash
poetry run pytest tests/unit/test_preprocess.py tests/unit/test_issue_route.py -q
```

**Pass criteria:** authentic images score ≥ 0.7; AI images ≤ 0.3; corrupt uploads return 400.

---

## 8. Tier 2 — Golden dataset regression (TC-001–003)

Dataset: `qa/test_cases/golden/` (67 images, `manifest.json`).

| Label | Count | TC | Expected score | Expected status |
|-------|------:|-----|----------------|-----------------|
| `authentic` | 30 | TC-001 | 0.8 – 1.0 | `compliant` |
| `ai_generated` | 37 | TC-002 | 0.0 – 0.3 | `non-compliant` |
| `edited` | 0 | TC-003 | 0.3 – 0.7 | `review` — **no images yet** |

```bash
export PYTHONPATH=src

# Full golden regression + suite accuracy gates (≥ 85%, FPR/FNR ≤ 10%)
poetry run pytest tests/integration/test_scoring_regression.py -v

# Export scores to CSV for tuning review
python3 scripts/export_golden_scores.py
# → qa/test_cases/golden/scoring_report.csv
```

**Provenance index:** authentic photos in `qa/test_cases/authentic/` are indexed for pHash matching. The regression harness rebuilds this index automatically.

**Pass criteria:** `test_per_image_score_bands` and `test_suite_level_accuracy_and_error_rates` pass.

---

## 9. Tier 3 — RAG pipeline (`/api/query`)

Requires: **local Qdrant**, **ingested PDFs**, **Mistral API key**.

### 9.1 Regulation PDFs

Five PDFs must exist in `research/regulations/`:

```
research/regulations/
├── eu_ai_act.pdf
├── gdpr.pdf
├── codigo_penal.pdf
├── lopdgdd.pdf
└── ley_13_2022.pdf
```

See `research/regulations/README_Maxim.md` for source requirements.

### 9.2 Start Qdrant (Docker)

```bash
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  qdrant/qdrant
```

Verify:

```bash
curl http://localhost:6333/collections
```

Stop/remove later:

```bash
docker stop qdrant && docker rm qdrant
```

### 9.3 Ingest PDFs (one-time per Qdrant volume)

```bash
set -a && source src/.env && set +a
export PYTHONPATH=src
export QDRANT_URL=http://localhost:6333

poetry run python -m scripts.ingest
# → "Ingestion complete."
```

This recreates the `regulations` collection, chunks PDFs (~512 tokens, 64 overlap), embeds locally, and writes vectors to Qdrant. **Re-run after wiping the Qdrant container.**

### 9.4 Start API with RAG

```bash
set -a && source src/.env && set +a
export PYTHONPATH=src

poetry run uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Startup calls `load_index()` — watch logs for `Failed to build index during startup`. If Qdrant is down, the API still starts but `/api/query` returns **503**.

### 9.5 Smoke `/api/query`

```bash
curl -s -X POST http://127.0.0.1:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What transparency obligations apply to AI-generated media under the EU AI Act?"}' \
  | python3 -m json.tool
```

**Pass criteria:**

| Check | Expected |
|-------|----------|
| HTTP status | `200` |
| `answer` | Non-empty synthesized text |
| `regulation_refs` | At least one entry |
| Each ref | `regulation` and `article` are not `"Unknown"` |

**Suggested smoke questions** (for TC-005 manual eval):

| # | Question | Expected regulation |
|---|----------|---------------------|
| 1 | GDPR lawful basis for processing personal data in images? | GDPR |
| 2 | Transparency rules for deepfakes under EU AI Act? | EU AI Act |
| 3 | Digital product passport obligations for electronics? | ESPR / codigo penal context |
| 4 | How does LOPDGDD supplement GDPR in Spain? | LOPDGDD |
| 5 | Ley 13/2022 audiovisual communication requirements? | Ley 13/2022 |

### 9.6 TC-005 (RAG metrics)

Automated TC-005 is not fully wired yet. For manual evaluation, see [INTEGRATION_AND_QA_RUNBOOK.md](./INTEGRATION_AND_QA_RUNBOOK.md) § Task 4 (precision ≥ 80%, recall ≥ 75%, hallucination ≤ 5%).

---

## 10. Tier 4 — VC payload without Sybol (mocked)

Validates scoring → RAG → VC JSON shape **without** calling Sybol.

```bash
poetry run pytest tests/unit/test_vc_schema.py tests/integration/test_vc_pipeline.py -v
```

Also covers **TC-006** (W3C VC 1.1 schema, required fields, `regulationRefs`, `evidenceUrl`).

To inspect a payload manually:

```bash
PYTHONPATH=src python3 -c "
from credentials.vc_builder import build_vc_payload
from rag.models import ComplianceResult, RegulationRef
from scoring.models import ComplianceStatus, ScoringResult, SignalBreakdown

result = ScoringResult(
    authenticity_score=0.86,
    score_breakdown=SignalBreakdown(m=0.9, a=0.8, v=0.85, p=0.9),
    compliance_status=ComplianceStatus.COMPLIANT,
    media_hash='a' * 64,
    model_version='local-test',
)
rag = ComplianceResult(
    summary='Test summary',
    regulation_refs=[RegulationRef(regulation='EU AI Act', article='50', source_url='/eu_ai_act.pdf', excerpt='...')],
)
print(build_vc_payload(result, rag, credential_id='urn:uuid:test', evidence_url='https://example.com/audit/1'))
"
```

**Pass criteria:** schema tests pass; payload contains `@context`, `type`, `credentialSubject`, `evidenceUrl`.

---

## 11. Tier 5 — Full issuance (`/api/issue` + Sybol)

This is the **only** tier that calls Sybol's remote API. Everything else stays local.

### 11.1 Prerequisites checklist

- [ ] Tier 3 complete (Qdrant ingested, `/api/query` returns 200)
- [ ] `MISTRAL_API_KEY` set
- [ ] Sybol tokens **or** email/password (see below)
- [ ] `SYBOL_DOCUMENT_ID` — catalog document for media compliance
- [ ] `SYBOL_ISSUER_KEY` — signing key from Sybol / wallet settings

### 11.2 Get Sybol tokens

**Option A — Wallet UI (recommended on develop)**

`openapi-share` documents `POST /auth/login`, but that path returns **404** on develop. The live backoffice login is:

```bash
curl -s -X POST 'https://api.develop.wallet.sybol.id/api/bo/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' | python3 -m json.tool
```

Or copy tokens from the browser:

1. Open `https://app.develop.wallet.sybol.id` (or URL Sybol gave you)
2. Log in
3. DevTools → Network → any API request
4. Copy `Authorization: Bearer …` → `SYBOL_ACCESS_TOKEN`
5. Copy `X-Id-Token: …` → `SYBOL_ID_TOKEN`

Tokens expire in ~1 hour.

**Option B — Login script**

```bash
export SYBOL_EMAIL=your@email
export SYBOL_PASSWORD='your-password'
PYTHONPATH=src poetry run python -m scripts.sybol_login
# Prints export lines to paste into src/.env
```

Note: `scripts.sybol_login` calls `/auth/login` on the base URL. If that returns 404, use Option A.

**Verify tokens:**

```bash
curl -s https://api.develop.wallet.sybol.id/auth/me \
  -H "Authorization: Bearer $SYBOL_ACCESS_TOKEN" \
  -H "X-Id-Token: $SYBOL_ID_TOKEN" | python3 -m json.tool
```

### 11.3 Discover catalog IDs

```bash
set -a && source src/.env && set +a
PYTHONPATH=src poetry run python -m scripts.sybol_discover_catalog --search media
```

Set in `src/.env`:

```env
SYBOL_DOCUMENT_ID=<uuid from catalog>
SYBOL_ISSUER_KEY=<kms key id from Sybol>
```

If no MediaCompliance document exists, ask Iñigo (`inigo@sybol.id`) to create one in the catalog.

### 11.4 Probe issuance (without uploading an image)

```bash
PYTHONPATH=src python3 -m scripts.sybol_probe_issue
```

Runs auth → catalog list → dry issue with synthetic scoring data.

### 11.5 Full `/api/issue` smoke test

```bash
set -a && source src/.env && set +a
export PYTHONPATH=src

# API must be running with Qdrant + ingest complete
curl -s -X POST http://127.0.0.1:8000/api/issue \
  -F "file=@qa/test_cases/golden/authentic/ar_1.JPG" \
  | python3 -m json.tool
```

**Pass criteria:**

| Check | Expected |
|-------|----------|
| HTTP status | `200` |
| `status` | `"signed_vc_issued"` |
| `signed` | `true` |
| `signed_vc` | Contains `signed_token` or `proof` |
| `vc_payload` | Unsigned VC with `regulationRefs`, `evidenceUrl` |

**Error codes:**

| Status | Meaning |
|--------|---------|
| `400` | Bad file type or scoring error |
| `502` | Sybol API rejected the request |
| `503` | RAG/audit unavailable, or Sybol env not configured |

---

## 12. Readiness checklist script

```bash
./scripts/check_demo_readiness.sh
```

Reports status for:

- Golden dataset presence
- Regulation PDFs (5/5)
- Local Qdrant on `:6333`
- `MISTRAL_API_KEY` and Sybol vars in `src/.env`

---

## 13. Troubleshooting

### Scoring is slow on first request

The HuggingFace deepfake model downloads once (~100 MB). Subsequent requests are faster.

### `/api/query` returns 503

```json
{"detail": "RAG pipeline not available. Ensure Qdrant is running and the index has been initialized."}
```

1. `docker ps` — is Qdrant running?
2. `curl http://localhost:6333/collections` — does `regulations` exist?
3. Re-run `poetry run python -m scripts.ingest`
4. Restart FastAPI after ingest

### Ingest fails with "No regulation PDFs found"

Add PDFs to `research/regulations/` with exact stems from `README_Maxim.md`.

### `/api/issue` returns 503 — Sybol not configured

Ensure **all** of these are set (not `TBD_*` placeholders):

- `SYBOL_DOCUMENT_ID`
- `SYBOL_ISSUER_KEY`
- `SYBOL_ACCESS_TOKEN` + `SYBOL_ID_TOKEN` (or `SYBOL_EMAIL` + `SYBOL_PASSWORD`)

### Sybol login returns 401 or 404

| Symptom | Fix |
|---------|-----|
| `404` on `/auth/login` | Use `/api/bo/auth/login` or wallet UI tokens |
| `401` on `/api/bo/auth/login` | Ask Sybol to provision user on develop tenant |
| `challengeName` in response | Complete MFA / password reset in wallet UI |

### Env vars not picked up

```bash
set -a && source src/.env && set +a   # re-export
# or restart uvicorn with --env-file src/.env
```

### Golden regression fails after scoring changes

```bash
python3 scripts/export_golden_scores.py   # inspect CSV
# optional tuning:
PYTHONPATH=src python3 scripts/fit_platt_calibration.py
```

---

## 14. Quick reference matrix

| What you test | Command / endpoint | Qdrant | Mistral | Sybol |
|---------------|-------------------|--------|---------|-------|
| Automated unit tests | `pytest tests/unit/` | mocked | mocked | mocked |
| VC schema (TC-006) | `pytest tests/unit/test_vc_schema.py` | mocked | mocked | mocked |
| Golden scoring (TC-001–002) | `pytest tests/integration/test_scoring_regression.py` | — | — | — |
| Health | `GET /health` | — | — | — |
| Scoring API | `POST /api/analyze` | — | — | — |
| RAG API | `POST /api/query` | ✅ local | ✅ cloud | — |
| Full VC issuance | `POST /api/issue` | ✅ local | ✅ cloud | ✅ cloud |
| Sybol auth only | `scripts.sybol_login` / DevTools | — | — | ✅ |
| Sybol issue probe | `scripts.sybol_probe_issue` | — | — | ✅ |

---

## Related docs

- [README.md](../README.md) — project overview
- [DEMO_RUNBOOK.md](./DEMO_RUNBOOK.md) — June demo paths
- [INTEGRATION_AND_QA_RUNBOOK.md](./INTEGRATION_AND_QA_RUNBOOK.md) — RAG metrics, Railway (production)
- [qa/test_cases/README_Saba.md](../qa/test_cases/README_Saba.md) — TC definitions
- [src/.env.example](../src/.env.example) — env template

---

*Last updated: June 2026 — matches `devel` branch layout.*
