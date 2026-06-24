# Integration & QA Runbook

Step-by-step guide for the four remaining operational tasks before the 25 June demo:

1. **RAG** — Qdrant up → ingest PDFs → smoke `/api/query`
2. **E2E** — smoke `/api/issue` once Sybol unblocks
3. **Railway** — production env vars (Qdrant, Mistral, Sybol)
4. **RAG metrics** — precision / recall / hallucination (TC-005)

**Owners (from project plan):** Alex / Darius (RAG + Railway), Darius (Sybol), Youssef + Saba (TC-005 metrics).

---

## Prerequisites

| Requirement | Status | Action |
|-------------|--------|--------|
| Poetry installed | — | `poetry install --with dev` |
| Five regulation PDFs in `research/regulations/` | **Missing** | Maxim must add files (see below) |
| Mistral API key | Needed for `/api/query` and `/api/issue` | Get from [Mistral console](https://console.mistral.ai/) |
| Qdrant instance | Local or Railway | Docker locally or Railway service |
| Sybol Cognito tokens | **Blocked** | Darius → Iñigo (`inigo@sybol.id`) |

### Required PDF filenames

Place complete official documents in `research/regulations/` (not summaries):

```
research/regulations/
├── eu_ai_act.pdf
├── gdpr.pdf
├── espr_dpp.pdf
├── lopdgdd.pdf
└── ley_13_2022.pdf
```

See `research/regulations/README_Maxim.md` for details.

### Load environment variables

The app reads from the process environment (`os.getenv`). A `src/.env` file is **not** loaded automatically — export it before running ingest or the API:

```bash
cp src/.env.example src/.env
# Edit src/.env with real values, then:
set -a && source src/.env && set +a
```

---

## Task 1 — RAG: Qdrant up → ingest PDFs → smoke `/api/query`

### 1.1 Start Qdrant

**Local (development):**

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Verify:

```bash
curl http://localhost:6333/collections
```

Expected: JSON with `"status":"ok"` (collection list may be empty before ingest).

**Railway (staging/production):**

1. In the Railway project, add a new service from image `qdrant/qdrant`.
2. Attach a **persistent volume** mounted at `/qdrant/storage`.
3. Note the internal hostname (e.g. `qdrant.railway.internal`) for the FastAPI service env vars.

### 1.2 Configure env for ingest

```bash
# Local
export QDRANT_URL=http://localhost:6333

# Railway (from your laptop, use the public URL or railway run)
export QDRANT_URL=http://qdrant.railway.internal:6333   # inside Railway network
export QDRANT_API_KEY=<your-qdrant-api-key>             # if auth is enabled
```

### 1.3 Run PDF ingest (one-time per Qdrant instance)

From the **project root**, with PDFs present and env vars exported:

```bash
PYTHONPATH=src poetry run python -m scripts.ingest
```

What this does:

- Reads PDFs from `research/regulations/` via `SimpleDirectoryReader`
- Chunks at ~512 tokens with 64-token overlap (`src/rag/ingest.py`)
- Embeds locally with `sentence-transformers/all-MiniLM-L6-v2` (no external embedding API)
- Writes vectors to the Qdrant collection `regulations` (recreates collection on each run)

Success output:

```
Ingestion complete.
```

**Common failures:**

| Error | Cause | Fix |
|-------|-------|-----|
| `FileNotFoundError: No regulation PDFs found` | No `.pdf` files in `research/regulations/` | Add the five PDFs |
| Connection refused to Qdrant | Qdrant not running or wrong `QDRANT_URL` | Start Qdrant / fix URL |
| Ingest slow on first run | Embedding model download | Wait; model is cached after first run |

**Ingest against Railway Qdrant from your laptop:**

```bash
railway link          # select the project
railway run bash -c 'set -a && source src/.env && set +a && PYTHONPATH=src poetry run python -m scripts.ingest'
```

Or point `QDRANT_URL` at Qdrant's public Railway URL if exposed.

### 1.4 Start the API

```bash
set -a && source src/.env && set +a
export QDRANT_URL=http://localhost:6333   # if local
export MISTRAL_API_KEY=<your-key>

PYTHONPATH=src poetry run uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

On startup the app calls `load_index()` and attaches to the existing `regulations` collection. It does **not** re-ingest automatically.

Check logs: no `Failed to build index during startup` exception. If Qdrant is down, the app still starts but RAG endpoints return **503**.

### 1.5 Smoke test `/api/query`

**Health check first:**

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

**Query (JSON body must include `question`):**

```bash
curl -s -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What transparency obligations apply to AI-generated media under the EU AI Act?"}' \
  | python3 -m json.tool
```

**Pass criteria:**

| Check | Expected |
|-------|----------|
| HTTP status | `200` |
| `answer` | Non-empty string citing regulations from context |
| `regulation_refs` | At least one entry |
| Each ref | `regulation` and `article` are **not** `"Unknown"` |
| No 503 | Index loaded at startup |

Example shape:

```json
{
  "answer": "...",
  "regulation_refs": [
    {
      "regulation": "EU AI Act",
      "article": "50",
      "url": "/path/to/eu_ai_act.pdf"
    }
  ]
}
```

**503 troubleshooting:**

```json
{"detail": "RAG pipeline not available. Ensure Qdrant is running and the index has been initialized."}
```

→ Re-run ingest, confirm `QDRANT_URL`, restart API.

**Alternative:** use Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs) → `POST /api/query`.

### 1.6 Suggested smoke questions

Use these for manual smoke and as seeds for TC-005:

| # | Question | Expected regulation (approx.) |
|---|----------|-------------------------------|
| 1 | What are GDPR lawful-basis requirements for processing personal data in images? | GDPR |
| 2 | What transparency rules apply to deepfakes under the EU AI Act? | EU AI Act |
| 3 | What digital product passport obligations exist for electronics? | ESPR/DPP |
| 4 | How does LOPDGDD supplement GDPR in Spain? | LOPDGDD |
| 5 | What does Ley 13/2022 require for audiovisual communication? | Ley 13/2022 |

---

## Task 2 — E2E: smoke `/api/issue` (after Sybol unblocks)

`/api/issue` runs the full pipeline: **score → RAG → Qdrant audit trail → build VC → Sybol sign**.

### 2.1 Blocker — what Sybol must provide

Contact **Iñigo García de Mata** (`inigo@sybol.id`). Darius leads; copy Javier on technical questions.

| # | Item | Why |
|---|------|-----|
| 1 | Valid Cognito `access_token` and `id_token` | `SybolClient` sends `Authorization: Bearer` + `x-id-token` |
| 2 | Confirm signing endpoint | Default: `POST https://api.sybol.io/api/bl/credentials` |
| 3 | `MEDIA_COMPLIANCE_CREDENTIAL` in Sybol catalog | VC type must be registered |
| 4 | Issuer DID | Resolved server-side from tenant auth (confirm with Iñigo) |

Until real tokens replace `TBD_*` placeholders, the route returns:

```json
{
  "detail": "Sybol signing is not configured — set SYBOL_API_URL, SYBOL_ACCESS_TOKEN, and SYBOL_ID_TOKEN."
}
```

HTTP **503**.

The client treats any value starting with `TBD_` as unconfigured (`src/credentials/sybol_client.py`).

### 2.2 Prerequisites (all must be green)

- [ ] Task 1 complete (Qdrant ingested, `/api/query` returns 200)
- [ ] `MISTRAL_API_KEY` set
- [ ] `SYBOL_ACCESS_TOKEN` and `SYBOL_ID_TOKEN` are real JWTs (not `TBD_*`)
- [ ] `SYBOL_API_URL=https://api.sybol.io/api/bl/credentials` (or confirmed alternative)

### 2.3 Smoke test `/api/issue`

Use a small authentic JPEG/PNG/WebP (e.g. from `qa/test_cases/authentic_raw/`):

```bash
curl -s -X POST http://localhost:8000/api/issue \
  -F "file=@qa/test_cases/authentic_raw/ar_1.JPG" \
  | python3 -m json.tool
```

**Pass criteria:**

| Check | Expected |
|-------|----------|
| HTTP status | `200` |
| `status` | `"signed_vc_issued"` |
| `signed` | `true` |
| `signed_vc` | Object containing `proof` |
| `vc_payload` | Unsigned VC with `credentialSubject.regulationRefs`, `evidenceUrl` |

Example success shape:

```json
{
  "status": "signed_vc_issued",
  "vc_id": "urn:uuid:...",
  "detail": "Signed VC issued by Sybol",
  "signed": true,
  "vc_payload": { "...": "..." },
  "signed_vc": { "proof": { "...": "..." } }
}
```

**Error codes:**

| Status | Meaning |
|--------|---------|
| `400` | Unsupported file type or `ScoringError` |
| `502` | Sybol API error (`SybolSigningError`) — check `railway logs` / app logs |
| `503` | RAG unavailable, audit write failed, or Sybol not configured |

### 2.4 Production smoke (Railway)

Replace `localhost:8000` with your Railway app URL:

```bash
curl -s https://<your-app>.up.railway.app/health
curl -s -X POST https://<your-app>.up.railway.app/api/issue \
  -F "file=@qa/test_cases/authentic_raw/ar_1.JPG"
```

### 2.5 E2E checklist (log for QA / paper Ch. 5)

```
[ ] /health → 200
[ ] /api/analyze → 200 with score + compliance_status
[ ] /api/query → 200 with regulation_refs
[ ] /api/issue → 200 with signed_vc.proof
[ ] evidenceUrl in vc_payload points to Qdrant audit record
[ ] regulationRefs match RAG output (no Unknown articles)
```

---

## Task 3 — Railway: production env vars

Configure variables on **two Railway services**: the FastAPI app and Qdrant.

### 3.1 Qdrant service

| Setting | Value |
|---------|-------|
| Image | `qdrant/qdrant` |
| Volume mount | `/qdrant/storage` |
| Port | `6333` (default) |

Optional: enable API key auth in Qdrant and store the key for the FastAPI service.

### 3.2 FastAPI service — required variables

In Railway → **FastAPI service** → **Variables**:

| Variable | Required for | Example / notes |
|----------|--------------|-----------------|
| `MISTRAL_API_KEY` | `/api/query`, `/api/issue` | Mistral console API key |
| `QDRANT_URL` | RAG + audit | `http://qdrant.railway.internal:6333` (private network) |
| `QDRANT_API_KEY` | Qdrant auth | Only if Qdrant auth is enabled |
| `QDRANT_COLLECTION` | RAG index | Default: `regulations` |
| `QDRANT_AUDIT_COLLECTION` | Audit trail | Default: `media_audit` |
| `SYBOL_API_URL` | `/api/issue` | `https://api.sybol.io/api/bl/credentials` |
| `SYBOL_ACCESS_TOKEN` | `/api/issue` | Cognito access token (JWT) |
| `SYBOL_ID_TOKEN` | `/api/issue` | Cognito id token (JWT) |
| `SYBOL_REQUEST_TIMEOUT` | `/api/issue` | `10.0` (seconds) |

Copy the template from `src/.env.example` and replace placeholders.

**Do not commit real secrets.** Set them only in the Railway dashboard.

### 3.3 Deploy and verify

`railway.toml` already configures:

```toml
startCommand = "sh -c 'uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}'"
healthcheckPath = "/health"
```

After deploy:

```bash
curl https://<your-app>.up.railway.app/health
railway logs   # no index startup exceptions
```

### 3.4 Post-deploy: ingest into production Qdrant

The API does not ingest on boot. After first deploy (or after wiping Qdrant volume):

1. Ensure PDFs are in the repo or available in the ingest environment.
2. Run ingest against production `QDRANT_URL` (see Task 1.3).
3. Redeploy or restart FastAPI so `load_index()` reconnects.

### 3.5 Railway checklist

```
[ ] Qdrant service running with persistent volume
[ ] FastAPI linked to GitHub (auto-deploy from main, per team policy)
[ ] All variables above set in Railway (no TBD_* for Sybol when going live)
[ ] Ingest completed against production Qdrant
[ ] /health → 200 on public URL
[ ] /api/query → 200 on public URL
```

---

## Task 4 — RAG metrics: precision / recall / hallucination (TC-005)

**Test case:** TC-005 — RAG query returns relevant regulation refs with no hallucinated laws.

**Acceptance thresholds (project scope):**

| Metric | Target |
|--------|--------|
| Precision | ≥ 80% |
| Recall | ≥ 75% |
| Hallucination rate | ≤ 5% |

**Owners:** Youssef (evaluation harness + golden questions), Saba (pytest TC-005), Maxim (legal validation of citations).

### 4.1 Definitions (for this project)

Work at the **citation level** (`regulation_refs` entries), not free-text answer quality alone.

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Precision** | relevant citations returned ÷ total citations returned | Are the refs we return correct? |
| **Recall** | relevant citations returned ÷ expected citations for question | Did we find the refs we should? |
| **Hallucination rate** | hallucinated citations ÷ total citations returned | Citations wrong, fabricated, or `Unknown` |

A citation is **hallucinated** if any of the following hold:

- `regulation` or `article` is `"Unknown"` (the pipeline filters these in `query_regulations`, but check the answer text too)
- Article number does not exist in the source PDF
- Regulation name does not match any ingested document
- Citation is irrelevant to the question (Maxim validates)

The code already drops refs with `Unknown` regulation/article (`src/rag/query.py` → `_validate_refs`).

### 4.2 Build the golden question set

Create `qa/rag_eval/questions.jsonl` (one JSON object per line):

```json
{"id": "Q01", "question": "What are GDPR lawful-basis requirements for processing personal data in images?", "expected": [{"regulation": "GDPR", "articles": ["5", "6"]}]}
{"id": "Q02", "question": "What transparency obligations apply to AI-generated synthetic media?", "expected": [{"regulation": "EU AI Act", "articles": ["50"]}]}
{"id": "Q03", "question": "What digital product passport requirements apply to electronics?", "expected": [{"regulation": "ESPR/DPP (EU 2024/1781)", "articles": []}]}
```

Aim for **≥ 20 questions** covering all five regulations. Maxim should mark `expected` articles after reading the PDFs.

### 4.3 Manual evaluation procedure

1. Complete Task 1 (ingest + working `/api/query`).
2. For each question, call `/api/query` and save the response.
3. For each returned `regulation_refs` entry, label it **relevant** or **irrelevant** (Maxim).
4. For each expected article, mark **found** if any returned ref matches regulation + article.
5. Compute per-question and aggregate metrics.

**Scoring spreadsheet columns:**

| question_id | returned_regulation | returned_article | relevant? | hallucinated? | expected_article | found? |

**Aggregate:**

```
precision = sum(relevant returned) / sum(all returned)
recall    = sum(found expected) / sum(all expected)
hallucination_rate = sum(hallucinated returned) / sum(all returned)
```

**TC-005 pass:** all three metrics meet thresholds on the golden set.

### 4.4 Automated harness (recommended)

`ragas` / `deepeval` are mentioned in the project scope but **not yet in `pyproject.toml`**. Two options:

**Option A — Lightweight script (no new deps)**

Add a script `scripts/eval_rag.py` that:

1. Loads `qa/rag_eval/questions.jsonl`
2. Calls `query_regulations()` in-process (or hits `/api/query`)
3. Matches returned refs against `expected` with fuzzy regulation name match
4. Prints precision, recall, hallucination rate and writes `qa/rag_eval/results.json`

**Option B — ragas (richer LLM-judged metrics)**

```bash
poetry add --group dev ragas datasets
```

Use ragas `context_precision`, `context_recall`, and faithfulness scores on the same golden set. Map ragas outputs to the project thresholds and document the mapping in the QA log.

### 4.5 Pytest TC-005 (Saba)

Add `tests/e2e/test_tc005_rag.py` (or under `tests/integration/`) that:

1. Skips if `MISTRAL_API_KEY` or Qdrant index unavailable (`pytest.mark.integration`)
2. Posts known questions to `/api/query`
3. Asserts:
   - status 200
   - `regulation_refs` non-empty
   - no ref has `regulation == "Unknown"` or `article == "Unknown"`
   - at least one expected regulation name appears (from fixture)

Run:

```bash
set -a && source src/.env && set +a
poetry run pytest tests/e2e/test_tc005_rag.py -v -m integration
```

### 4.6 QA log template

Record results in the team QA log (Section 3.5 of project doc):

```markdown
## TC-005 — RAG query evaluation
- Date:
- Environment: local | Railway
- Questions evaluated: N
- Precision: X% (target ≥ 80%)
- Recall: Y% (target ≥ 75%)
- Hallucination rate: Z% (target ≤ 5%)
- Pass/Fail:
- Notes: (edge cases, Maxim review items)
```

### 4.7 TC-005 checklist

```
[ ] Golden question set (≥ 20) with Maxim-validated expected articles
[ ] Task 1 complete (live index)
[ ] Manual or scripted eval run
[ ] Precision ≥ 80%, Recall ≥ 75%, Hallucination ≤ 5%
[ ] Results logged for paper Chapter 5
[ ] pytest TC-005 added (optional but recommended)
```

---

## Quick reference — dependency matrix

| Endpoint | Qdrant + ingest | MISTRAL_API_KEY | Sybol tokens |
|----------|-----------------|-----------------|--------------|
| `GET /health` | — | — | — |
| `POST /api/analyze` | — | — | — |
| `POST /api/query` | ✅ | ✅ | — |
| `POST /api/issue` | ✅ | ✅ | ✅ |

---

## Related docs

- [PROJECT_STATUS.md](./PROJECT_STATUS.md) — current blockers and scorecard
- [README.md](../README.md) — local setup
- [src/credentials/README_Darius.md](../src/credentials/README_Darius.md) — Sybol + Railway notes
- [src/rag/README_Alex.md](../src/rag/README_Alex.md) — RAG pipeline design
- [qa/test_cases/README_Saba.md](../qa/test_cases/README_Saba.md) — TC-001–006 definitions
- [research/regulations/README_Maxim.md](../research/regulations/README_Maxim.md) — PDF requirements

---

*Update this runbook when Sybol unblocks, PDFs land, or Railway URLs are finalized.*
