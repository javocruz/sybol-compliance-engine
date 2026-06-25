# Notes for Alex — demo handoff

Last updated: 2026-06-25 (Javier). Branch `feat/local-ready` merged into `main`.

---

## TL;DR — about the Sybol tokens you keep being asked for

> `SYBOL_ACCESS_TOKEN=eyJ...`
> `SYBOL_ID_TOKEN=eyJ...`

**We do NOT need Sybol to "create" these tokens for us.** They are short-lived
(~1 hour) and **generated on the fly** by our own client every time we call the
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
loads fine and already shows our issued **"Media Compliance"** credentials with
all 11 claims, so the full signing path is confirmed end to end.

---

## What is done (all on `main` now)

- **Scoring TC-001/002/003**: golden set is 77 images (30 authentic / 37 AI /
  10 edited from Youssef). Regression passes **77/77**. Edited images now land in
  the `review` band via a new "re-saved edited" profile in `src/scoring/`.
- **Full pipeline** works locally: `/api/analyze`, `/api/query` (Mistral + RAG),
  `/api/issue` (Sybol-signed VC), and the `sybol_e2e_full_issue` script.
- **RAG citations** now resolve real article numbers (EN "Article" + ES
  "Artículo"/"Art.", carried forward across chunks). Re-ingest with
  `PYTHONPATH=src python3 -m scripts.ingest` if you rebuild the index.
- **Frontend** (your React app) builds and talks to the API. Fixed the Vite dev
  proxy to target `127.0.0.1` (was `localhost` → could resolve to IPv6 `::1` and
  break the UI→API connection), and regulation "view source" links now honor
  `VITE_API_BASE_URL`.
- **Tests**: full suite 171 passed / 2 env-skipped. Frontend `npm run build` ok.

---

## What is left for the demo

1. **Visual click-through of the UI** — run it and click Analyze / Query / Issue
   once on screen (everything is verified programmatically, just not by eye):

   ```bash
   # terminal 1
   PYTHONPATH=src uvicorn src.api.main:app --host 127.0.0.1 --port 8000
   # terminal 2
   cd frontend && npm ci && npm run dev    # http://127.0.0.1:5173
   ```

2. **Decide where we present from.**
   - **Local** is ready today (recommended, lowest risk).
   - **Server (`52.210.252.91`)** is still blocked: `javier` is not in the
     `docker` group, so Qdrant can't run there. Needs Pelayo to add us to
     `docker`, then ingest + run uvicorn (systemd). Treat as stretch.

3. **Demo-morning pre-flight**: `./scripts/check_demo_readiness.sh` (expect all
   `[OK]`), Qdrant + uvicorn up, a few test images ready (1 authentic, 1 AI,
   1 edited).

## Known cosmetic limits (safe to demo)

- EU AI Act citations retrieved from **recitals/preamble** show no article number
  (there isn't one — they precede the articles). The UI hides the chip in that
  case, so it just shows "EU AI Act". Spanish regs and AI Act article bodies show
  real numbers.
- `evidence_url` in issued VCs points at `http://localhost:6333/...` (the local
  Qdrant audit point). Fine for a local demo; needs a public URL if we go server.

---

## Development backlog (post-demo / general)

Not needed for tomorrow, but this is the real "what's left to build/harden" list.

### Deployment & infra
- **Server deploy (`52.210.252.91`)**: add `javier` (+ `alex`) to the `docker`
  group, run Qdrant there, ingest the corpus, run the API under **systemd** (not a
  foreground uvicorn), open port 8000 / put it behind a reverse proxy.
- **Railway path**: the Dockerfile is API-only — it does not build the frontend.
  Either add an `npm ci && npm run build` stage that emits `frontend/dist`, or
  deploy `frontend/` as a separate static site with `VITE_API_BASE_URL` pointing
  at the API. (See `docs/RAILWAY_SETUP.md`.)
- **Qdrant persistence**: confirm a mounted volume + a backup/restore plan so the
  index survives restarts; document re-ingest as the recovery step.
- **Public `evidence_url`**: today it points at local Qdrant. Production VCs need a
  durable, publicly resolvable audit URL (object storage or an API audit route).
- **Secrets management**: move off plaintext `src/.env` for prod (Railway/Vercel
  env vars or a secrets manager). Never commit `.env` or `deploy/` keys.

### Sybol / credentials
- **Token caching**: we re-login to Cognito on every issue call (~adds latency).
  Cache the access token for its ~1h lifetime and refresh on expiry.
- **VC verification + revocation**: we issue signed VCs but have no verify flow or
  `credentialStatus`/revocation story. Add a verify endpoint and decide on
  revocation.

### RAG quality (TC-005)
- **Article granularity for the AI Act**: recital chunks have no article. Consider
  splitting/tagging at article boundaries during ingestion, and optionally
  capturing recital numbers, so EU AI Act citations are article-precise.
- **Full green metrics run**: precision/recall/hallucination harness is wired and
  labels are aligned, but a clean pass is gated by Mistral dev-tier rate limits.
  Run it against a higher-tier key (or Ollama) to record real numbers.
- **Production LLM resilience**: the 429 backoff lives only in the test harness.
  The production `/api/query` makes a single call (fine for demo), but for
  throughput add retry/backoff there and/or a paid Mistral tier.
- **Ollama path**: integrated but unvalidated end-to-end — needs `ollama serve` +
  model pulled, then verify `/api/query?llm_provider=ollama` as an offline fallback.

### Scoring
- **Milder edited batch**: current TC-003 images are heavily re-encoded JPEGs. A
  batch of light edits that keep EXIF would exercise the original `EDITED_PROFILE`
  path and broaden coverage.
- **Real-world robustness**: thresholds are calibrated to the 77-image golden set;
  validate against a larger/more varied set and consider Platt calibration (off by
  default) once we have enough labelled data.

### Frontend
- **Real browser QA**: error states, loading states, large-file handling,
  responsive/mobile, and the Issue tab against a slow `/api/issue`.
- **No frontend tests**: add a minimal vitest/RTL setup for the API client and the
  results components.

### Engineering hygiene
- **CI**: add GitHub Actions to run `pytest` + `npm run build` on every PR
  (Bugbot is manual today).
- **Observability**: structured logging + error tracking; silence/configure the
  OpenTelemetry import warning.
- **Remove `deploy/` keys from the repo working tree** — keep SSH keys outside the
  project directory.
