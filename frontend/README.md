# Sybol Compliance Engine — Web UI

Vite + React + TypeScript SPA for media authenticity scoring (**Analyze**), regulation Q&A via RAG (**Query**), and signed W3C Verifiable Credential issuance (**Issue**).

## Prerequisites

- **Node.js 18+** (LTS recommended)
- A running backend on port 8000 (see root [README](../README.md))

## Local development

Use two terminals from the repository root.

**Terminal 1 — backend**

```bash
PYTHONPATH=src poetry run uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — frontend**

```bash
cd frontend && npm ci && npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` and `/health` to `http://localhost:8000`, so you can leave `VITE_API_BASE_URL` unset (relative URLs).

The first `/api/analyze` request after a cold start may take 15–30 seconds while the ML model loads.

## Against EC2 (remote API)

To point the local Vite app at a backend running on EC2:

1. Copy the example env file: `cp .env.example .env`
2. Set `VITE_API_BASE_URL=http://<ec2-ip>:8000` (replace with your host)
3. Run `npm run dev`

The backend must allow CORS from `http://localhost:5173` (configured in `src/api/main.py`).

## Production build

Build the static assets, then serve UI and API from a single uvicorn process:

```bash
cd frontend && npm ci && npm run build
cd .. && poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Open `http://<host>:8000/` — same origin for UI and API; no CORS setup required.

`frontend/dist/` is gitignored; run `npm run build` on each deploy target (e.g. EC2) before starting uvicorn.

## Test images

Sample images for manual testing live in the repo (not bundled into `frontend/dist`):

- `qa/test_cases/golden/authentic/` — real / authentic media
- `qa/test_cases/golden/ai_generated/` — AI-generated samples

Upload any JPEG, PNG, or WebP from these folders in the Analyze tab.

## OpenAPI docs

Interactive API documentation: `http://<host>:8000/docs`

## Compliance thresholds (display only)

The backend computes `compliance_status`. The UI maps scores for reference:

| Status | Authenticity score |
|---|---|
| `compliant` | ≥ 0.7 |
| `review` | 0.3 – 0.7 |
| `non-compliant` | < 0.3 |

## Query tab — LLM providers

The Query tab includes a toggle between:

- **Mistral (cloud)** — requires `MISTRAL_API_KEY` in `src/.env`
- **Qwen local (Ollama)** — requires Ollama running with `qwen2.5:7b-instruct`

Your choice is saved in browser `localStorage` for testing convenience.

### Ollama setup (local or EC2)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b-instruct
# Ollama listens on http://localhost:11434 by default
```

Set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `src/.env` if needed. For `/api/issue` without the UI toggle, set `DEFAULT_LLM_PROVIDER=ollama`.

## Issue tab — Sybol VC signing

The Issue tab runs the full pipeline: image scoring, regulation lookup (RAG), audit trail write, and Sybol-signed VC issuance.

Requires in `src/.env`:

- **Qdrant** — `QDRANT_URL` and ingested regulations (same as Query tab)
- **LLM** — `MISTRAL_API_KEY` or local Ollama (`DEFAULT_LLM_PROVIDER=ollama`)
- **Sybol** — `SYBOL_DOCUMENT_ID`, `SYBOL_ISSUER_KEY`, and either `SYBOL_ACCESS_TOKEN` + `SYBOL_ID_TOKEN` or `SYBOL_EMAIL` + `SYBOL_PASSWORD`

If Sybol is not configured, the API returns HTTP 503 with setup instructions.
