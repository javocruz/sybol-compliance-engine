# Notes for Alex — demo handoff & server experiments

Last updated: 2026-06-25 (Javier). Everything below is on **`main`** (PR #12 merged).

Use this doc to run the stack locally, understand what's shipped, and pick up the EC2 deploy when disk is unblocked.

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

## EC2 server (`54.154.92.29`) — status & deploy plan

Pelayo's VM for IE/Sybol experiments. **IP changed 2026-06-25** after server restart (was `52.210.252.91`).

| Item | Status |
|------|--------|
| SSH as `javier` | Works — key `~/.ssh/sybol_ie_javier` |
| SSH as `alex` | Should work once your key is on the box (ask Pelayo) |
| Docker group | **OK** — `docker ps` works |
| Disk | **Fixed** — **38 GB** volume, **~23 GB free** (41% used) — ready for torch + models |
| Sudo / systemd | **Blocked** — `sudo` needs password; use tmux for uvicorn or ask Pelayo for systemd |
| Qdrant / API on server | **Not deployed yet** — no containers, no repo clone (fresh after restart) |
| AWS SG port 8000 | **Closed** externally until API runs + Pelayo opens inbound TCP 8000 |

### Deploy sequence (summary)

Full steps were written in the deploy plan; condensed for you:

```bash
# SSH
ssh -i ~/.ssh/sybol_ie_javier javier@54.154.92.29

# Clone
git clone https://github.com/javocruz/sybol-compliance-engine.git
cd sybol-compliance-engine && git checkout main

# Qdrant (localhost only — do NOT bind 6333 to 0.0.0.0)
docker run -d --name sybol-qdrant --restart unless-stopped \
  -p 127.0.0.1:6333:6333 -v sybol_qdrant_data:/qdrant/storage qdrant/qdrant

# Python — IMPORTANT: CPU-only torch on this host (no GPU)
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install poetry
poetry export -f requirements.txt --without-hashes --only main -o /tmp/req.txt
grep -v '^torch==' /tmp/req.txt > /tmp/req-notorch.txt   # torch already installed
pip install -r /tmp/req-notorch.txt

# Secrets — copy src/.env from a teammate (never commit); chmod 600
# Set QDRANT_URL=http://127.0.0.1:6333
# Set PUBLIC_BASE_URL=http://54.154.92.29:8000  (public evidenceUrl for VCs)

# Ingest + API
export PYTHONPATH=src HF_HOME=$HOME/.cache/huggingface
python3 -m scripts.ingest
# GET /api/audit/{id} serves audit JSON publicly when PUBLIC_BASE_URL is set
# Prefer systemd (needs sudo); fallback: tmux + uvicorn on 0.0.0.0:8000

# Frontend: build on your laptop, rsync dist/
# cd frontend && VITE_API_BASE_URL= npm run build
# rsync -avz -e "ssh -i ~/.ssh/sybol_ie_javier" dist/ javier@54.154.92.29:~/sybol-compliance-engine/frontend/dist/
```

**Public demo URL (once up):** `http://54.154.92.29:8000/` (API + bundled UI).

**Rollback:** `docker stop sybol-qdrant`; stop uvicorn/systemd; `rm -rf ~/sybol-compliance-engine`.

---

## What is left (post-demo)

1. **Server deploy** — disk is ready; clone repo → Qdrant → venv → ingest → uvicorn → rsync frontend → open SG :8000.
2. **Public evidence URL** — `evidenceUrl` still points at localhost Qdrant unless we add a public audit route.
3. **Docs/CI cleanup** — update `PROJECT_STATUS.md`, export RAG metrics to `qa/rag_eval/results.json`.

---

## Known cosmetic limits (safe to demo)

- EU AI Act **recital** chunks have no article number — UI shows regulation name only.
- `evidenceUrl` in VCs uses `QDRANT_URL` (localhost on laptop) — not clickable from wallet for external viewers.
- AI images often show **exactly 0.26** — synthetic-profile **cap**, not a bug; raw scores differ slightly below the cap.
- **Platt disabled** — document as optional future work, not a missing switch.

---

## Development backlog (post-demo)

### Deployment & infra
- Complete EC2 deploy on `54.154.92.29` (disk OK; Qdrant + ingest + uvicorn + frontend dist).
- Open **inbound TCP 8000** on AWS security group for audience URL.
- Railway: Dockerfile is API-only; add frontend build stage or separate static deploy.
- Public `evidence_url` (not raw Qdrant localhost).
- Secrets off plaintext `src/.env` in prod.

### Sybol / credentials
- Token caching (avoid Cognito login every issue).
- VC verify + revocation flow.
- VC Data Model **2.0** migration (we emit **1.1** today).

### RAG (TC-005)
- Record formal precision/recall/hallucination numbers (harness ready; Mistral 429 on batch runs).
- Ollama path: `llm_provider=ollama` — needs local `ollama serve` + model pull.
- AI Act article-level tagging for recital chunks.

### Scoring
- Milder edited images (EXIF retained) for broader TC-003.
- Larger hold-out set before enabling Platt (`PLATT_ENABLED` stays `False` for now).

### Frontend
- Browser QA (errors, loading, mobile).
- Optional vitest for API client + result components.

### Engineering
- GitHub Actions: pytest + `npm run build` on PRs.
- Do not commit `deploy/` SSH key material — keep keys outside the repo.

---

## Message template for Pelayo (SG port 8000)

> Hola Pelayo — gracias por el reinicio y el disco ampliado. La nueva IP es 54.154.92.29 y SSH funciona. ¿Podéis abrir el puerto **8000** en el security group para la URL pública de la demo? Gracias.
