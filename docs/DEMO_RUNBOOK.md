# Demo Runbook — Recommended Path (June 25)

Full pipeline is **live on develop**: **`POST /api/issue`** scores an image, grounds
it in EU/Spanish regulation via RAG, writes an audit trail, and returns a
Sybol-signed W3C Verifiable Credential.

Guaranteed demo: **`POST /api/analyze`** (scoring only, no external services).  
Recommended demo: **`POST /api/issue`** (full signed-VC pipeline).

---

## Step 1 — Sybol auth (automatic, no token copying)

The engine logs in to Sybol develop directly via AWS Cognito
(`USER_PASSWORD_AUTH`), so you do **not** need to copy tokens from the browser.

1. Put the IE service account in `src/.env` (never commit):

```bash
SYBOL_EMAIL=info@ie.id
SYBOL_PASSWORD=<password from Pelayo's access email>
SYBOL_API_BASE_URL=https://api.develop.wallet.sybol.id
SYBOL_DOCUMENT_ID=0acdb1ed-4cd2-41a4-917a-b7270d6166b9
```

The Cognito client id and issuer DID already have working develop defaults in
`src/.env.example`.

2. Verify login and catalog access:

```bash
PYTHONPATH=src python3 -m scripts.sybol_login          # prints "Login OK"
PYTHONPATH=src python3 -m scripts.sybol_discover_catalog
```

Tokens are minted per request, so there is nothing to refresh during the demo.

3. Inspect issued credentials in the wallet UI at
   [https://sybol.develop.wallet.sybol.id/](https://sybol.develop.wallet.sybol.id/)
   (log in with `info@ie.id`). Use this to confirm a VC issued from `/api/issue`
   appears in the wallet.

> Manual token override (only if Cognito login ever fails): log into the wallet
> UI, open DevTools - Network, and copy the `Authorization` bearer into
> `SYBOL_ACCESS_TOKEN` and `X-Id-Token` into `SYBOL_ID_TOKEN`.

---

## Step 2 — Option F: RAG pipeline (parallel with Maxim)

**Blocker:** PDFs not in repo yet (`research/regulations/`).

When Maxim adds these files:

- `eu_ai_act.pdf`
- `gdpr.pdf`
- `codigo_penal.pdf`
- `lopdgdd.pdf`
- `ley_13_2022.pdf`

Run:

```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
PYTHONPATH=src python3 -m scripts.ingest
```

Add to `src/.env`:

```bash
QDRANT_URL=http://localhost:6333
MISTRAL_API_KEY=your_key
```

Test RAG:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What EU rules apply to AI-generated media disclosure?"}'
```

Check readiness anytime:

```bash
./scripts/check_demo_readiness.sh
```

---

## Step 3 — Fallback contact for Iñigo (only if develop breaks)

Auth, the `MEDIA_COMPLIANCE_IE` catalog, and signing are all working on develop,
so this is only a fallback if the develop environment changes under us. Contact
Iñigo if Cognito login starts returning `NotAuthorized` for `info@ie.id`, or if
the catalog document `0acdb1ed-4cd2-41a4-917a-b7270d6166b9` disappears.

---

## Step 4 — Guaranteed demo (Option D): Scoring only

Works **today** without Sybol, Qdrant, or Mistral.

```bash
poetry install --with dev   # or: pip install -e ".[dev]"
cp src/.env.example src/.env   # optional for /issue later

PYTHONPATH=src uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
# Authentic image (expect compliant, score ~0.7–1.0)
curl -s -X POST http://localhost:8000/api/analyze \
  -F "file=@qa/test_cases/golden/authentic/ar_1.JPG" | python3 -m json.tool

# AI image (expect non-compliant or review)
curl -s -X POST http://localhost:8000/api/analyze \
  -F "file=@qa/test_cases/golden/ai_generated/$(ls qa/test_cases/golden/ai_generated | head -1)" | python3 -m json.tool
```

Interactive docs: http://localhost:8000/docs

**Demo script (2 min):**

1. Show problem: no machine-readable proof of media authenticity.
2. Upload authentic photo → score + breakdown `m,a,v,p` → `compliant`.
3. Upload AI image → lower score → `non-compliant`.
4. Upload edited photo → mid score → `review`.
5. Run `/api/issue` to ground the score in regulation and return the Sybol-signed VC (show Architecture.md diagram).

Run golden regression (optional QA slide):

```bash
PYTHONPATH=src python3 -m pytest tests/integration/test_scoring_regression.py -v --tb=no -q
```

---

## Step 5 — Recommended demo: Full `/api/issue` (signed VC)

Requires:

| Requirement | Env var / action |
|-------------|------------------|
| Sybol auth | `SYBOL_EMAIL` + `SYBOL_PASSWORD` (Cognito login, automatic) |
| Catalog doc | `SYBOL_DOCUMENT_ID` (develop default already set) |
| Signing key | `SYBOL_ISSUER_KEY` (develop default already set) |
| Qdrant + ingest | `QDRANT_URL` + PDFs ingested (`scripts.ingest`) |
| Mistral | `MISTRAL_API_KEY` |

```bash
curl -s -X POST http://localhost:8000/api/issue \
  -F "file=@qa/test_cases/golden/authentic/ar20.jpg" | python3 -m json.tool
```

Success: `"status": "signed_vc_issued"` with a signed token in `signed_vc`.
A scripted end-to-end run (score → RAG → audit → signed VC) is also available:

```bash
PYTHONPATH=src python3 -m scripts.sybol_e2e_full_issue qa/test_cases/golden/authentic/ar20.jpg
```

---

## Quick reference — what each endpoint needs

| Feature | Needs |
|---------|------------|
| `/api/analyze` | Nothing — ready |
| `/api/query` | Qdrant ingested + Mistral key |
| `/api/issue` | Above + Sybol `SYBOL_EMAIL`/`SYBOL_PASSWORD` (catalog + issuer have develop defaults) |
