# Railway Setup Guide

Deploy the **Sybol Compliance Engine** on [Railway](https://railway.app) with two services:

1. **FastAPI app** — scoring, RAG, VC issuance (`src.api.main:app`)
2. **Qdrant** — vector store for regulation PDFs + audit trail

```
┌─────────────────────┐      private network      ┌─────────────────────┐
│  FastAPI service    │ ────────────────────────▶ │  Qdrant service     │
│  (this repo)        │   QDRANT_URL :6333        │  qdrant/qdrant      │
│  /health            │                           │  volume: /qdrant/   │
│  /api/analyze       │                           │         storage     │
│  /api/query         │                           └─────────────────────┘
│  /api/issue         │
└─────────────────────┘
         │
         ▼
   Mistral API (external)
   Sybol API (external, when configured)
```

**Time estimate:** ~30–45 minutes for first-time setup (excluding PDF ingest).

---

## Prerequisites

| Item | Notes |
|------|-------|
| Railway account | [railway.app](https://railway.app) — Hobby or Pro (persistent volumes need a paid plan) |
| GitHub repo access | Admin on `sybol-compliance-engine` for GitHub ↔ Railway connect |
| Mistral API key | Required for `/api/query` and `/api/issue` |
| Regulation PDFs | Five PDFs in `research/regulations/` before ingest (see `research/regulations/README_Maxim.md`) |
| Sybol tokens | Optional until `/api/issue` signing is needed — contact Iñigo via Darius |

**Local tools (optional but useful):**

```bash
npm install -g @railway/cli   # Railway CLI
poetry install --with dev     # for running ingest locally or via railway run
```

---

## Step 1 — Create a Railway project

### Option A — Dashboard (recommended for team setup)

1. Go to [railway.app/new](https://railway.app/new).
2. Choose **Deploy from GitHub repo**.
3. Select `sybol-compliance-engine`.
4. Railway creates a first service from the repo — this becomes the **FastAPI** service.

### Option B — CLI

```bash
cd /path/to/sybol-compliance-engine
railway login
railway init        # create new project
railway link        # link to existing project
```

---

## Step 2 — Add the Qdrant service

The FastAPI app does **not** bundle Qdrant. Add it as a separate service in the **same Railway project** so private networking works.

### Dashboard

1. In your Railway project, click **+ New** → **Empty Service** (or **Docker Image**).
2. Set the image to `qdrant/qdrant` (official Qdrant image).
3. Rename the service to `qdrant` (lowercase — this affects the internal hostname).

### Persistent storage (required)

Without a volume, Qdrant data is lost on every redeploy.

1. Open the **Qdrant service** → **Volumes**.
2. Click **Add Volume**.
3. Mount path: `/qdrant/storage`
4. Size: start with **1 GB** (regulation index is small; audit records grow slowly).

### Expose port

1. Open **Qdrant service** → **Settings** → **Networking**.
2. Ensure port **6333** is the service port (Qdrant HTTP API default).
3. **Do not** expose Qdrant publicly unless you need ingest from outside Railway — prefer private networking only.

### Note the internal URL

Services in the same project reach each other at:

```text
http://<service-name>.railway.internal:<port>
```

If you named the service `qdrant`:

```text
http://qdrant.railway.internal:6333
```

This is the value for `QDRANT_URL` on the FastAPI service.

---

## Step 3 — Configure the FastAPI service

### Build settings

The repo ships both `Dockerfile` and `railway.toml`. Railway typically detects the Dockerfile automatically.

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage Poetry build, Python 3.12, runs uvicorn on `$PORT` |
| `railway.toml` | Start command + health check override |

`railway.toml` contents:

```toml
[deploy]
startCommand = "sh -c 'uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}'"
healthcheckPath = "/health"
restartPolicyType = "on_failure"
```

**Dashboard checks:**

1. Open the **FastAPI service** → **Settings** → **Build**.
2. Confirm builder is **Dockerfile** (or Nixpacks if Dockerfile is disabled — Dockerfile is preferred for reproducibility).
3. Root directory: `/` (repo root).

### Public domain

1. Open **FastAPI service** → **Settings** → **Networking**.
2. Click **Generate Domain** to get a public URL like `sybol-compliance-engine-production.up.railway.app`.
3. Use this URL for health checks and API calls.

### Resource sizing

First deploy downloads heavy dependencies (`torch`, `sentence-transformers`, deepfake model ~100 MB on first request). Recommend:

| Setting | Suggested value |
|---------|-----------------|
| Memory | **2 GB** minimum |
| CPU | 2 vCPU if available |

If the service crashes on startup with OOM, increase memory in **Settings → Resources**.

---

## Step 4 — Environment variables

Set these on the **FastAPI service** (not Qdrant), in **Variables** tab.

Copy from `src/.env.example` and replace placeholders. **Never commit real secrets to git.**

### Required for RAG (`/api/query`, `/api/issue`)

| Variable | Example | Description |
|----------|---------|-------------|
| `MISTRAL_API_KEY` | `sk-...` | Mistral Large API key for RAG synthesis |
| `QDRANT_URL` | `http://qdrant.railway.internal:6333` | Internal Qdrant URL (same Railway project) |
| `QDRANT_API_KEY` | *(optional)* | Only if Qdrant API key auth is enabled |

### Optional Qdrant tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_COLLECTION` | `regulations` | RAG index collection name |
| `QDRANT_AUDIT_COLLECTION` | `media_audit` | Audit trail collection for `/api/issue` |
| `APP_ENV` | `dev` | Set to `production` in prod |

### Required for VC signing (`/api/issue`)

| Variable | Example | Description |
|----------|---------|-------------|
| `SYBOL_API_URL` | `https://api.sybol.io/api/bl/credentials` | Sybol businessLogic signing endpoint |
| `SYBOL_ACCESS_TOKEN` | Cognito JWT | `Authorization: Bearer` token |
| `SYBOL_ID_TOKEN` | Cognito JWT | Sent as `x-id-token` header |
| `SYBOL_REQUEST_TIMEOUT` | `10.0` | HTTP timeout in seconds |

**Sybol blocker:** values starting with `TBD_` are treated as unconfigured. `/api/issue` returns **503** until real tokens are set.

### Not needed on Railway

Railway injects `PORT` automatically. Do not hardcode it.

### Shared variables (optional)

If both services need the same key, use Railway **Shared Variables** at the project level — but only `QDRANT_API_KEY` is relevant across services; Mistral and Sybol keys belong on FastAPI only.

---

## Step 5 — Deploy

### GitHub auto-deploy (production)

1. FastAPI service → **Settings** → **Source** → **Connect Repo** (if not already).
2. Enable **Auto Deploy**.
3. Set branch to `main` (team policy: develop on `devel`, deploy prod from `main`).

```text
Push to main → GitHub Actions CI → Railway auto-deploy → /health check
```

CI runs on `devel` pushes and PRs to `devel`/`main` (see `.github/workflows/ci.yml`). Merge to `main` only after tests pass.

### Manual deploy (CLI)

```bash
railway link                  # select project + FastAPI service
railway up                    # deploy current directory
railway logs                  # watch startup
```

### Verify deployment

```bash
curl https://<your-app>.up.railway.app/health
```

Expected:

```json
{"status":"ok"}
```

Check logs for index startup:

```bash
railway logs --service <fastapi-service-name>
```

- **OK:** app starts even if Qdrant is temporarily down (by design).
- **Warning:** `Failed to build index during startup` — Qdrant unreachable or collection empty. `/api/analyze` still works; `/api/query` returns 503.

---

## Step 6 — Ingest regulation PDFs into production Qdrant

The API **does not ingest PDFs on boot**. You must run ingest once (and again after wiping the Qdrant volume).

### Prerequisites

Place these files in `research/regulations/`:

```
eu_ai_act.pdf
gdpr.pdf
espr_dpp.pdf
lopdgdd.pdf
ley_13_2022.pdf
```

### Option A — Run ingest via Railway CLI (recommended)

Runs inside Railway's network so `qdrant.railway.internal` resolves:

```bash
railway link    # select the FastAPI service

railway run bash -c '
  export QDRANT_URL=http://qdrant.railway.internal:6333
  export MISTRAL_API_KEY=not-needed-for-ingest
  PYTHONPATH=src poetry run python -m scripts.ingest
'
```

Ingest only needs Qdrant — Mistral is not used during embedding (local `sentence-transformers`).

### Option B — Run ingest locally against public Qdrant URL

Only if you exposed Qdrant with a public Railway URL:

```bash
export QDRANT_URL=https://<qdrant-public-url>
export QDRANT_API_KEY=<if-set>
PYTHONPATH=src poetry run python -m scripts.ingest
```

### Option C — One-off Railway job service

If `railway run` times out (large PDFs + model download), temporarily scale up memory or run ingest from a machine with repo + PDFs pointed at a reachable `QDRANT_URL`.

### After ingest

Restart or redeploy the FastAPI service so `load_index()` attaches to the populated `regulations` collection:

```bash
railway redeploy
```

---

## Step 7 — Smoke test endpoints

Replace `<your-app>` with your Railway domain.

```bash
# Health
curl https://<your-app>.up.railway.app/health

# Scoring only (no Qdrant/Mistral needed)
curl -X POST https://<your-app>.up.railway.app/api/analyze \
  -F "file=@qa/test_cases/authentic_raw/ar_1.JPG"

# RAG (needs ingest + MISTRAL_API_KEY)
curl -s -X POST https://<your-app>.up.railway.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What GDPR articles apply to processing personal data in images?"}' \
  | python3 -m json.tool

# Full pipeline (needs Sybol tokens too)
curl -s -X POST https://<your-app>.up.railway.app/api/issue \
  -F "file=@qa/test_cases/authentic_raw/ar_1.JPG" \
  | python3 -m json.tool
```

| Endpoint | Needs |
|----------|-------|
| `/health` | Nothing |
| `/api/analyze` | Nothing external |
| `/api/query` | Qdrant ingested + `MISTRAL_API_KEY` |
| `/api/issue` | Above + valid `SYBOL_*` tokens |

Interactive docs: `https://<your-app>.up.railway.app/docs`

---

## Step 8 — Ongoing operations

### View logs

```bash
railway logs --service <fastapi-service-name>
railway logs --service qdrant
```

Or use the Railway dashboard **Observability** tab.

### Redeploy after env var changes

Changing variables triggers a redeploy automatically. If not:

```bash
railway redeploy
```

### Re-ingest after PDF updates

```bash
# Same as Step 6 — ingest recreates the regulations collection
railway run bash -c 'export QDRANT_URL=http://qdrant.railway.internal:6333 && PYTHONPATH=src poetry run python -m scripts.ingest'
railway redeploy
```

### Branch workflow

| Branch | Purpose |
|--------|---------|
| `devel` | Active development, CI on every push |
| `main` | Production auto-deploy on Railway |

Do not push directly to `main` without review.

---

## Troubleshooting

### Deploy fails / service won't start

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| OOM crash | `torch` + models need RAM | Increase memory to 2 GB+ |
| Build timeout | Large Poetry install | Retry; consider Dockerfile cache |
| Health check fails | App not listening on `$PORT` | Confirm `railway.toml` / Dockerfile use `${PORT}` |

### `/api/query` returns 503

```json
{"detail":"RAG pipeline not available. Ensure Qdrant is running and the index has been initialized."}
```

| Check | Action |
|-------|--------|
| `QDRANT_URL` | Must be `http://qdrant.railway.internal:6333` (service name must match) |
| Qdrant running | `railway logs --service qdrant` |
| Collection exists | Run ingest (Step 6) |
| FastAPI restarted after ingest | `railway redeploy` |

### `/api/issue` returns 503 (Sybol)

```json
{"detail":"Sybol signing is not configured — set SYBOL_API_URL, SYBOL_ACCESS_TOKEN, and SYBOL_ID_TOKEN."}
```

Replace `TBD_*` placeholders with real Cognito JWTs from Sybol.

### `/api/issue` returns 502

Sybol API rejected the request. Check FastAPI logs for the Sybol error body. Common causes: expired tokens, unregistered VC type, schema mismatch.

### Qdrant data lost after redeploy

Volume not mounted at `/qdrant/storage`. Add the volume (Step 2) and re-run ingest.

### Ingest: `No files found in research/regulations`

No PDFs in the repo. Add the five regulation PDFs locally, commit or upload them, then re-run ingest. The ingest CLI reads from the filesystem — when using `railway run`, the repo files must be present in the deployed context (they are if deploying from GitHub with PDFs committed).

### Internal networking not working

- Both services must be in the **same Railway project/environment**.
- Service name in URL must match exactly (e.g. `qdrant` → `qdrant.railway.internal`).
- Use `http://` not `https://` for internal URLs.

---

## Setup checklist

Copy this into your team channel when done:

```
Railway setup
[ ] Project created
[ ] Qdrant service (image qdrant/qdrant, volume at /qdrant/storage)
[ ] FastAPI service connected to GitHub
[ ] Public domain generated for FastAPI
[ ] Env vars set: MISTRAL_API_KEY, QDRANT_URL, QDRANT_* 
[ ] Sybol vars set (or acknowledged as blocked)
[ ] Deploy succeeded, /health → 200
[ ] Regulation PDFs in repo
[ ] Ingest completed against production Qdrant
[ ] /api/query smoke test → 200 with regulation_refs
[ ] /api/issue smoke test → 200 (when Sybol unblocks)
[ ] Auto-deploy from main enabled
```

---

## Related docs

- [INTEGRATION_AND_QA_RUNBOOK.md](./INTEGRATION_AND_QA_RUNBOOK.md) — RAG ingest, E2E, TC-005 metrics
- [PROJECT_STATUS.md](./PROJECT_STATUS.md) — blockers and current status
- [src/credentials/README_Darius.md](../src/credentials/README_Darius.md) — Sybol integration details
- [README.md](../README.md) — local development

---

*Maintained by the infra team (Darius / Alex). Update when Railway URLs or service names change.*
