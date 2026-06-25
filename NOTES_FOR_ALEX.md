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
