# Sybol Compliance Engine — Project Status

**Last updated:** 20 June 2026  
**Team lead:** Javier Cruz  
**Partner:** Sybol — Iñigo García de Mata (CTO), Pelayo (Product)  
**Presentation deadline:** 25 June 2026, 16:00  
**Repository baseline:** `main` @ `bfe5d59` (PR #5 + #6 merged)

This document is the single source of truth for what has been built, what remains, and how close the project is to its stated goals.

---

## Executive summary

The **Compliance AI Engine** is a FastAPI service that scores media authenticity against EU regulatory requirements and issues a W3C Verifiable Credential via Sybol's identity infrastructure.

| Area | Status | Notes |
|------|--------|-------|
| Core scoring pipeline | **Done** | Four signals + profile rules; golden-set calibrated |
| RAG compliance engine | **Code done, PDFs in repo** | 5/5 regulations; Qdrant ingest pending |
| VC payload construction | **Mostly done** | VC 1.1-style payload; some VC 2.0 fields deferred |
| Sybol signing integration | **Scaffolded, blocked** | OpenAPI v4 client ready; develop auth + catalog pending |
| Automated tests | **Done** | **122 tests**, ~90% coverage |
| QA golden dataset | **Partial** | 67 images (30 authentic, 37 AI); **0 edited** |
| Research paper | **Not started** | No `paper/draft.md` |
| End-to-end demo | **Partially ready** | `/api/analyze` works; `/api/issue` blocked on Sybol + RAG |

**Bottom line:** Core engineering is roughly **~85% complete**. Remaining work is dominated by external dependencies (Sybol access, regulation PDFs), QA completion (edited images, RAG metrics, e2e), and presentation deliverables (paper, demo script).

---

## Project goals

### Problem statement

There is no standardized, machine-readable way to prove whether a piece of media is authentic and which EU regulations apply. This project connects media scoring, regulatory retrieval, and cryptographically signed credentials into one pipeline.

### What we are building

1. **Media Authenticity Scoring** — Four signals (`m`, `a`, `v`, `p`) combined into a score in `[0.0, 1.0]` with compliance status mapping.
2. **RAG Compliance Engine** — Ingests EU regulation PDFs, retrieves relevant articles, and produces structured `regulationRefs`.
3. **Verifiable Credential Issuance** — Encodes score, breakdown, regulation citations, and audit trail into a W3C VC signed through Sybol BusinessWallet.

### Deliverables (priority order)

| Priority | Deliverable | Deadline | Status |
|----------|-------------|----------|--------|
| **Primary** | Research paper | 25 Jun 2026 | Not started |
| **Secondary** | Functional demo (upload → score → signed VC) | 25 Jun 2026 | Partial — analyze ready; signing blocked |
| **Tertiary** | Production-ready Sybol integration | 25 Jun 2026 (stretch) | Scaffolded on develop API |

### Compliance score interpretation

| Score range | Status | Meaning |
|-------------|--------|---------|
| 0.0 – 0.3 | `non-compliant` | Likely AI-generated or deepfake |
| 0.3 – 0.7 | `review` | Partially authentic or edited |
| 0.7 – 1.0 | `compliant` | Passes signal checks |

---

## Team and ownership

| Person | Area | Primary responsibilities |
|--------|------|--------------------------|
| **Javier Cruz** | Technical lead | Scoring, VC payload, docs, Sybol coordination |
| **Alex Garcia Perdriau** | RAG & backend | PDF ingest, Qdrant, `/query`, Railway |
| **Darius-Luca Petruti** | Infra & Sybol | CI/CD, Railway, deployment env |
| **Saba Zarandia** | QA lead | pytest harness, TC-001–006, QA log |
| **Youssef Ayman** | QA & RAG eval | Golden dataset extensions, RAG metrics |
| **Maxim Heller** | Research / legal | Regulation PDFs, paper Ch. 3, DPIA |
| **Jana Eltoni** | Research / paper | Ch. 1 & 4, demo script and slides |

---

## Component status

### 1. Media scoring (`src/scoring/`)

| Item | Status | Details |
|------|--------|---------|
| Four signals (`m`, `a`, `v`, `p`) | Done | Metadata, artifacts, visual, provenance |
| Format-aware artifacts | Done | PNG/no-EXIF path weights fake probability |
| Profile rules in `scorer.py` | Done | Provenance floor, EXIF-rich floor, synthetic cap, edited clamp |
| Golden-set calibration | Done | **67/67** TC band pass; see `scoring_report.csv` |
| Provenance reference index | Done | 30 photos in `qa/test_cases/authentic/` |
| Platt scaling | Optional | `scripts/fit_platt_calibration.py`; `PLATT_ENABLED = False` |
| `POST /api/analyze` | Done | No external deps required |

**Caveat:** Authentic golden labels rely on the same photos being in the provenance reference index. Production use requires a real reference corpus.

---

### 2. RAG compliance engine (`src/rag/`)

| Item | Status |
|------|--------|
| Ingest, chunk, embed, Qdrant index, query pipeline | Done |
| Regulation PDFs in repo | **Done (5/5)** |
| Legal accuracy review | Not done |
| RAG eval harness (precision/recall/hallucination) | Not done |

**Corpus:** `eu_ai_act`, `gdpr`, `codigo_penal`, `lopdgdd`, `ley_13_2022` (in `research/regulations/`)

---

### 3. Verifiable credentials (`src/credentials/`)

| Item | Status |
|------|--------|
| VC payload builder + audit trail | Done |
| Sybol client (OpenAPI v4 catalog issuance) | Done (scaffold) |
| Catalog issue builder + probe scripts | Done |
| Live signing on develop | **Blocked** |
| VC 2.0 fields (`validFrom`, `credentialSchema`, `credentialStatus`) | Deferred |

---

### 4. API layer

| Endpoint | Status | Dependencies |
|----------|--------|--------------|
| `GET /health` | Live | None |
| `POST /api/analyze` | Live | Scoring only |
| `POST /api/query` | Live (503 if no index) | Qdrant + PDFs + Mistral |
| `POST /api/issue` | Live (503 if unconfigured) | Qdrant + Mistral + Sybol tokens |

---

### 5. Infrastructure

| Item | Status |
|------|--------|
| GitHub Actions CI on `main` | Done |
| `railway.toml` + Dockerfile | Done |
| Railway prod env (Qdrant, Sybol, Mistral) | Partial |
| Demo readiness script | `./scripts/check_demo_readiness.sh` |

---

## Testing and QA

### Automated tests

| Metric | Value |
|--------|-------|
| Total tests | **122** |
| Coverage | **~90%** (threshold 80%) |
| Golden regression | **67/67 pass** (TC-001, TC-002) |

### Test cases (TC-001–006)

| TC | Description | Status |
|----|-------------|--------|
| TC-001 | Authentic → 0.8–1.0, compliant | **Pass** (automated) |
| TC-002 | AI → 0.0–0.3, non-compliant | **Pass** (automated) |
| TC-003 | Edited → 0.3–0.7, review | **Blocked** — no edited images in manifest |
| TC-004 | Corrupted file → clean error | Partial (unit tests) |
| TC-005 | RAG query → valid refs | **Blocked** — no PDFs / Qdrant |
| TC-006 | VC valid schema | **Pass** (`test_vc_schema.py`) |

### QA deliverables still open

- Edited + corrupted images (Youssef)
- RAG metrics run (Youssef + Saba)
- `tests/e2e/` full workflow (Saba)
- QA log (Section 3.5 of scope doc)

See [qa/test_cases/README_Saba.md](../qa/test_cases/README_Saba.md).

---

## Sybol integration blockers (develop)

Verified 20 Jun 2026 (Cloudflare off — same results):

| Check | Result |
|-------|--------|
| `api.develop.wallet.sybol.id` | Resolves; catalog **200** |
| `app.develop.wallet.sybol.id` | **DNS does not resolve** |
| `POST /auth/login` | **404** |
| `POST /api/bl/auth/login` | **401** (`info@ie.id`) |
| Media compliance catalog entry | **Missing** |

**Owner:** Pelayo / Iñigo — wallet URL, account provisioning, `documentId`, `issuerKey`.

See [docs/DEMO_RUNBOOK.md](./DEMO_RUNBOOK.md) and [sybol_docs/openapi-wallet.yaml](../sybol_docs/openapi-wallet.yaml).

---

## Research and documentation

| Item | Owner | Status |
|------|-------|--------|
| [Architecture.md](../Architecture.md) | Javier | Done |
| [docs/DEMO_RUNBOOK.md](./DEMO_RUNBOOK.md) | Javier | Done |
| [qa/test_cases/README_Saba.md](../qa/test_cases/README_Saba.md) | Javier / Saba | Done |
| `docs/vc_schema.md` | Javier | Missing |
| `paper/draft.md` | Team | Not started |
| Demo script + slides | Jana | Not started |
| DPIA | Maxim | Not started |

---

## Environment variables

Copy `src/.env.example` → `src/.env` (never commit).

| Variable | Required for |
|----------|--------------|
| `MISTRAL_API_KEY` | `/api/query`, `/api/issue` |
| `QDRANT_URL` | `/api/query`, `/api/issue` |
| `SYBOL_API_BASE_URL` | Sybol client (default: develop API) |
| `SYBOL_ACCESS_TOKEN`, `SYBOL_ID_TOKEN` | `/api/issue` signing |
| `SYBOL_DOCUMENT_ID`, `SYBOL_ISSUER_KEY` | Catalog issuance |

---

## Acceptance criteria

| Criterion | Target | Measured? |
|-----------|--------|-----------|
| Test coverage | ≥ 80% | **Yes — ~90%** |
| Scoring accuracy (golden) | ≥ 85% | **Yes — 100%** on current set |
| FPR / FNR | ≤ 10% | **Yes** on golden regression |
| VC schema pass rate | 100% | **Yes** |
| VC issuance success | ≥ 95% | No (Sybol blocked) |
| RAG precision / recall | ≥ 80% / ≥ 75% | No |
| Hallucination rate | ≤ 5% | No |

---

## What works today

```bash
poetry install --with dev
PYTHONPATH=src pytest tests/unit tests/integration -q
./scripts/check_demo_readiness.sh
PYTHONPATH=src uvicorn api.main:app --reload --port 8000
```

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@qa/test_cases/golden/authentic/ar_1.JPG"
```

Full pipeline (when unblocked):

1. `docker run -p 6333:6333 qdrant/qdrant`
2. Add PDFs → `PYTHONPATH=src python3 -m scripts.ingest`
3. Set Sybol tokens in `src/.env`
4. `POST /api/issue`

---

## Remaining work (before 25 June)

| # | Action | Owner |
|---|--------|-------|
| 1 | Unblock Sybol develop (email sent to Pelayo) | Javier → Pelayo/Iñigo |
| 2 | Add 5 regulation PDFs + ingest | Maxim → Alex |
| 3 | Add edited images to golden set | Youssef |
| 4 | Run QA suite on `main`; write QA log | Saba |
| 5 | Demo script + slides (analyze-first narrative) | Jana |
| 6 | Paper draft + chapters | Team |
| 7 | Smoke `/api/issue` once Sybol responds | Javier / Darius |
| 8 | Railway prod env vars | Darius |

---

## Summary scorecard

| Workstream | Progress | Blocker |
|------------|----------|---------|
| Scoring engine | █████████░ 95% | Edited images; production reference corpus |
| RAG engine | ███████░░░ 70% | PDFs + legal review |
| VC issuance | ██████░░░░ 65% | Sybol tokens + catalog |
| API & deployment | ████████░░ 85% | Prod env + ingest |
| Automated testing | █████████░ 95% | E2E tests |
| QA validation | ██████░░░░ 60% | TC-003–005, QA log |
| Research paper | ░░░░░░░░░░ 0% | All chapters |
| Demo readiness | ██████░░░░ 55% | Sybol + RAG + script |

---

## References

- [README.md](../README.md)
- [docs/AI Lab Summer Work.md](./AI%20Lab%20Summer%20Work.md)
- [Architecture.md](../Architecture.md)
- [docs/DEMO_RUNBOOK.md](./DEMO_RUNBOOK.md)
- [qa/test_cases/README_Saba.md](../qa/test_cases/README_Saba.md)
- [src/credentials/README_Darius.md](../src/credentials/README_Darius.md)
- [research/regulations/README_Maxim.md](../research/regulations/README_Maxim.md)

---

*Maintained by the technical team. Update this file when a major milestone is completed or a blocker is resolved.*
