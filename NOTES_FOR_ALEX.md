# Notes for Alex — demo handoff & server experiments

Last updated: 2026-06-26 (Javier). Post-ceremony roadmap implemented on `main`.

Use this doc to run the stack locally, operate the EC2 deploy, and understand what's shipped.

---

## Post-ceremony updates (Jun 26)

### Infrastructure
- **systemd unit:** `deploy/sybol-api.service` — bind `127.0.0.1:8000`, use Caddy on 443 for HTTPS
- **Deploy script:** `bash deploy/deploy.sh` on server (git pull, CPU torch, Qdrant, restart)
- **Monitoring:** `deploy/healthcheck.sh` + optional `SLACK_WEBHOOK_URL`
- Full runbook: [`deploy/README.md`](deploy/README.md)

### API
- Rich **`GET /api/status`** — git commit, uptime, chunk count, Platt flag, VC version
- **`GET /api/verify/{vc_id}`** / **`POST /api/revoke/{vc_id}`** — audit-based verification
- Rate limits on analyze/query/issue; optional **`API_KEYS`** for write endpoints
- Model warm-up: `WARMUP_ON_START=true`

### Frontend (Sybol branding)
- Satoshi font + Sybol palette from marketing site tokens
- Tabs: Analyze / Query / Issue / **System**
- Evidence URL prominent on Issue results
- Build: `cd frontend && npm ci && npm run build && npm test`

### Paper vs code
- See [`docs/PAPER_CODE_ALIGNMENT.md`](docs/PAPER_CODE_ALIGNMENT.md)

---

## TL;DR — about the Sybol tokens you keep being asked for

> `SYBOL_ACCESS_TOKEN=eyJ...`
> `SYBOL_ID_TOKEN=eyJ...`

**We do NOT need Sybol to "create" these tokens for us.** They are short-lived
(~1 hour) and **generated on the fly** by our client every time we call the
Sybol API.

- `POST /auth/login` returning **404** on develop is expected — that endpoint
  does not exist there. We authenticate with **AWS Cognito directly**
  (`USER_PASSWORD_AUTH`) using `SYBOL_EMAIL` + `SYBOL_PASSWORD`.
- The login + token minting lives in `src/credentials/cognito_auth.py` and is
  driven by `src/credentials/sybol_client.py`. You can see it work with:

  ```bash
  PYTHONPATH=src python3 -m scripts.sybol_login          # prints "Login OK"
  PYTHONPATH=src python3 -m scripts.sybol_e2e_full_issue qa/test_cases/golden/authentic/ar20.jpg
  ```

So the only secrets we actually need in `src/.env` are:

```bash
SYBOL_EMAIL=info@ie.id
SYBOL_PASSWORD=<the password from Pelayo's access email>
SYBOL_API_BASE_URL=https://api.develop.wallet.sybol.id
SYBOL_DOCUMENT_ID=0acdb1ed-4cd2-41a4-917a-b7270d6166b9   # MEDIA_COMPLIANCE_IE catalog
# SYBOL_ISSUER_KEY + Cognito client id have working develop defaults in src/.env.example
```

`SYBOL_ACCESS_TOKEN` / `SYBOL_ID_TOKEN` are only a **manual override** for the
rare case Cognito login fails — leave them unset and the client logs in itself.

The wallet UI ( https://sybol.develop.wallet.sybol.id/ , login `info@ie.id` )
loads fine and shows issued **"Media Compliance"** credentials (verified, all 11
claims). Full signing path is confirmed end to end.

---

## What we shipped on `main` (Jun 25)

### Scoring & golden dataset
- Golden set is **77 images**: 30 authentic / 37 AI / **10 edited** (Youssef).
- Regression **77/77** (TC-001 compliant, TC-002 non-compliant, TC-003 review).
- Edited images use a **re-saved edited profile** in `src/scoring/` (stripped-EXIF
  camera JPEGs, `m ≈ 0.39` → review band 0.35–0.60, exempt from synthetic cap).
- **Platt scaling stays off** (`PLATT_ENABLED = False`). Profile rules are what
  calibrate the bands; enabling Platt without refitting would risk breaking 77/77.

### Pipeline (local, verified)
- `/api/analyze`, `/api/query` (Mistral + Qdrant), `/api/issue` (Sybol-signed VC).
- `scripts/sybol_e2e_full_issue` — score → RAG → audit → signed VC.
- Provenance index: **30 authentic reference photos** in `qa/test_cases/authentic/`
  (authentic images get `p=1.0`; AI/edited get `p=0.0` unless matched).

### RAG
- Five PDFs ingested locally (~1795 Qdrant chunks).
- Article extraction at ingest: EN "Article" + ES "Artículo"/"Art." with
  carry-forward across chunks; UI hides "Article" chip when unknown.
- TC-005 harness in `tests/integration/test_rag_metrics.py` (3 tests); needs
  Qdrant + `MISTRAL_API_KEY` to run live metrics.

### Frontend (your React app)
- Merged from `devel`: Analyze / Query / Issue tabs.
- **Vite proxy fix**: targets `127.0.0.1:8000` (not `localhost` — avoids IPv6
  `::1` breakage on macOS).
- Regulation PDF links honor `VITE_API_BASE_URL` (same as `api/client.ts`).
- Build: `cd frontend && npm ci && npm run build` — API serves `frontend/dist`
  at `/` when present.

### Tests & QA
- **173 tests** collected by pytest (was ~122 in older slides — update decks).
- TC-003 done, TC-004 done (7 corrupted-input tests), TC-005 harness done.
- Full run (with env): `PYTHONPATH=src pytest tests/unit tests/integration tests/e2e -q`

### Docs
- `docs/DEMO_RUNBOOK.md` — Cognito login, wallet URL, recommended demo path.
- `qa/QA_LOG.md` — TC-003 integration entry (2026-06-25).

---

## Quick start — experiment locally (Alex)

**Prerequisites:** Docker (Qdrant), `src/.env` from `src/.env.example` + secrets.

```bash
git checkout main && git pull origin main

# 1. Qdrant
docker ps | grep qdrant || docker run -d --name sybol-qdrant -p 6333:6333 qdrant/qdrant

# 2. Python deps (pick one)
poetry install --with dev
# or: python3 -m venv .venv && source .venv/bin/activate && pip install poetry && poetry install --with dev

# 3. Ingest (only if Qdrant volume is empty)
PYTHONPATH=src python3 -m scripts.ingest

# 4. API
export $(grep -v '^#' src/.env | xargs)   # or rely on dotenv in app
PYTHONPATH=src uvicorn src.api.main:app --host 127.0.0.1 --port 8000

# 5. Frontend (separate terminal)
cd frontend && npm ci && npm run dev    # http://127.0.0.1:5173 → proxies to :8000

# 6. Smoke
./scripts/check_demo_readiness.sh
PYTHONPATH=src python3 -m scripts.sybol_e2e_full_issue qa/test_cases/golden/authentic/ar20.jpg
```

**Demo images to try:**

| File | Expected |
|------|----------|
| `qa/test_cases/golden/authentic/ar20.jpg` | ~0.83, compliant (iPhone 14 EXIF) |
| `qa/test_cases/golden/ai_generated/beach_dalle.png` | 0.26, non-compliant (synthetic cap) |
| `qa/test_cases/golden/edited/edit1.jpg` | ~0.38, review |

**Bundled UI (same as server plan):** build with empty API base, API serves SPA:

```bash
cd frontend && VITE_API_BASE_URL= npm run build
# then only uvicorn on :8000 — open http://127.0.0.1:8000/
```

---

## EC2 server (`54.154.92.29`) — deployed

| Item | Status |
|------|--------|
| Public URL | **http://54.154.92.29:8000/** |
| Qdrant | Running (`sybol-qdrant`, 1,773 chunks) |
| API | uvicorn (migrate to systemd — see `deploy/sybol-api.service`) |
| HTTPS | Configure Caddy — `deploy/Caddyfile`, set `PUBLIC_BASE_URL=https://…` |
| Elastic IP | Ask Pelayo — attach so IP survives reboot |

```bash
ssh -i ~/.ssh/sybol_ie_javier javier@54.154.92.29
cd ~/sybol-compliance-engine && bash deploy/deploy.sh
```

---

## What is left (optional hardening)

1. **Elastic IP + HTTPS domain** — `compliance.sybol.id` via Caddy
2. **systemd** — replace tmux (`sudo cp deploy/sybol-api.service /etc/systemd/system/`)
3. **Export RAG metrics** — `python qa/rag_eval/export_metrics.py` after live run

---

## Known cosmetic limits (safe to demo)

- EU AI Act **recital** chunks have no article number — UI shows regulation name only.
- **`evidenceUrl`** is public when `PUBLIC_BASE_URL` is set (EC2 demo OK).
- AI images often show **exactly 0.26** — synthetic-profile **cap**, not a bug.
- **Platt disabled by default** — `PLATT_ENABLED` env toggle; see paper alignment doc.
- **VC 1.1** — not 2.0; wallet compatibility first.
