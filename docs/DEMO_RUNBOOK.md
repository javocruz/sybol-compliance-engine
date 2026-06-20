# Demo Runbook — Recommended Path (June 25)

Guaranteed demo: **`POST /api/analyze`** (scoring only).  
Stretch goal: **`POST /api/issue`** (signed VC via Sybol).

---

## Step 1 — Option A: Get Sybol tokens (try first)

OpenAPI `/auth/login` is **404** on develop. Use the **wallet web UI** instead.

1. Open the BusinessWallet develop app (try in order):
   - `https://app.develop.wallet.sybol.id`
   - Or the URL Iñigo / Sybol gave you for IE login
2. Log in with `info@ie.id` and your password.
3. Open **DevTools → Network**, filter by `api` or `credentials`.
4. Click any authenticated request and copy headers:
   - `Authorization: Bearer eyJ...` → paste token only into `SYBOL_ACCESS_TOKEN`
   - `X-Id-Token: eyJ...` → paste into `SYBOL_ID_TOKEN`
5. Save to `src/.env` (never commit):

```bash
cp src/.env.example src/.env
# edit src/.env
```

6. Verify tokens:

```bash
PYTHONPATH=src python3 -m scripts.sybol_discover_catalog
PYTHONPATH=src python3 -m scripts.sybol_probe_issue
```

Tokens expire in ~1 hour. Re-copy from browser or use refresh flow when Sybol documents it.

---

## Step 2 — Option F: RAG pipeline (parallel with Maxim)

**Blocker:** PDFs not in repo yet (`research/regulations/`).

When Maxim adds these files:

- `eu_ai_act.pdf`
- `gdpr.pdf`
- `espr_dpp.pdf`
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

## Step 3 — Option B: Message to Iñigo (if Step 1 fails)

Send this (Spanish or English):

> Hola Iñigo — estamos integrando el Compliance Engine con BusinessWallet develop (`api.develop.wallet.sybol.id`).
>
> 1. Las credenciales `info@ie.id` devuelven **401** en `/api/bl/auth/login` y **NotAuthorized** en Cognito pool `eu-west-1_Lpg65AWPJ`. ¿Está el usuario provisionado en develop?
> 2. ¿Cuál es la URL correcta del wallet UI para login?
> 3. ¿Podéis crear un documento de catálogo **MediaCompliance** (claims: mediaHash, authenticityScore, scoreBreakdown, complianceStatus, regulationRefs, evidenceUrl) y enviarnos **documentId** e **issuerKey**?
>
> Gracias, Javier

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
3. Upload AI image → lower score → `non-compliant` or `review`.
4. Explain: RAG + signed VC wired in `/api/issue`, blocked on Sybol catalog + tokens (show Architecture.md diagram).

Run golden regression (optional QA slide):

```bash
PYTHONPATH=src python3 -m pytest tests/integration/test_scoring_regression.py -v --tb=no -q
```

---

## Step 5 — Stretch: Full `/api/issue` (Option C)

Requires **all** of:

| Requirement | Env var / action |
|-------------|------------------|
| Sybol tokens | `SYBOL_ACCESS_TOKEN`, `SYBOL_ID_TOKEN` |
| Catalog doc | `SYBOL_DOCUMENT_ID` (from discover script or Iñigo) |
| Signing key | `SYBOL_ISSUER_KEY` (from Iñigo / settings after login) |
| Qdrant + ingest | `QDRANT_URL` + PDFs ingested |
| Mistral | `MISTRAL_API_KEY` |

```bash
curl -s -X POST http://localhost:8000/api/issue \
  -F "file=@qa/test_cases/golden/authentic/ar_1.JPG" | python3 -m json.tool
```

Success: `"status": "signed_vc_issued"` with `signed_vc.signed_token` or `proof`.

---

## Quick reference — what blocks what

| Feature | Blocked by |
|---------|------------|
| `/api/analyze` | Nothing — ready |
| `/api/query` | PDFs + Qdrant ingest + Mistral |
| `/api/issue` | Above + Sybol tokens + documentId + issuerKey |
