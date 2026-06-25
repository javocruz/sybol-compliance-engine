# sybol-compliance-engine

`sybol-compliance-engine` is a Compliance AI Engine built by IEU Labs in collaboration with Sybol to score media authenticity against EU regulatory requirements and issue a W3C Verifiable Credential signed through Sybol's DID infrastructure.

## Confirmed Stack

| Layer | Technology |
|---|---|
| RAG framework | LlamaIndex |
| Vector database | Qdrant |
| LLM synthesis | Mistral Large |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Deepfake detection model | HuggingFace dima806/deepfake_vs_real_image_detection |
| Vision/signal processing | OpenCV |
| EXIF metadata extraction | ExifRead |
| Perceptual hashing | imagehash |
| API framework | FastAPI |
| Deployment platform | Railway |
| Credential standard | W3C VC Data Model 2.0 |

## Team

| Team Area | Members |
|---|---|
| Technical | Javier, Alex, Darius |
| Research | Maxim, Jana |
| QA | Youssef, Saba |

## Setup

### Prerequisites

- Python 3.10–3.13
- [Poetry](https://python-poetry.org/) (recommended) or pip

### Install dependencies

```bash
poetry install --with dev
```

Or with pip:

```bash
pip install -e ".[dev]"
```

On first run, the scoring pipeline downloads the deepfake detection model from HuggingFace (~100 MB). This happens once and is cached locally.

### Environment variables

Copy the example env file and fill in your values:

```bash
cp src/.env.example src/.env
```

| Variable | Required for | Description |
|---|---|---|
| `MISTRAL_API_KEY` | `/query` (Mistral provider) | Mistral Large API key for RAG synthesis |
| `DEFAULT_LLM_PROVIDER` | `/issue` | `mistral` or `ollama` — synthesis backend for issue RAG step |
| `OLLAMA_BASE_URL` | `/query`, `/issue` (Ollama provider) | Ollama API URL (default `http://localhost:11434`) |
| `OLLAMA_MODEL` | `/query`, `/issue` (Ollama provider) | Model tag (default `qwen2.5:7b-instruct`) |
| `QDRANT_URL` | `/query`, app startup | Qdrant instance URL (e.g. `http://localhost:6333`) |
| `QDRANT_API_KEY` | `/query` | Qdrant API key (optional for local Qdrant) |
| `SYBOL_*` | `/issue` | Sybol VC signing — pending Darius/Iñigo confirmation |

Scoring via `/api/analyze` does not require Qdrant or Mistral. If Qdrant is unavailable at startup, `/api/analyze` still works but `/api/query` returns 503 until Qdrant is running and the regulations index has been ingested.

### Ingest regulation PDFs (one-time, before `/query` works)

Place the five regulation PDFs in `research/regulations/` (see `research/regulations/README_Maxim.md`), start Qdrant, then run:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

```bash
PYTHONPATH=src poetry run python -m scripts.ingest
```

This chunks PDFs, embeds locally, and writes vectors to the `regulations` Qdrant collection. On API startup, the server calls `load_index()` to attach to that collection — it does not re-ingest automatically.

## Running the API

1. Create your local env file (once):

```bash
cp src/.env.example src/.env
```

For local Qdrant (optional, only needed for `/query`), set `QDRANT_URL=http://localhost:6333` in `src/.env`.

2. Start the server from the project root:

```bash
PYTHONPATH=src python3 -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

If you have Poetry installed:

```bash
PYTHONPATH=src poetry run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

3. Open the API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The first startup downloads the deepfake model (~100 MB) and may take 15–30 seconds.

Health check:

```bash
curl http://localhost:8000/health
```

## Web UI

A React SPA in [`frontend/`](frontend/) provides an **Analyze** tab for uploading images and viewing authenticity scores, and a **Query** tab for regulation Q&A via RAG. The Issue tab is a placeholder until Sybol VC signing is wired up.

**Query tab** requires Qdrant with an ingested regulations index. Choose **Mistral (cloud)** (`MISTRAL_API_KEY`) or **Qwen local (Ollama)** via the UI toggle. `/api/issue` uses `DEFAULT_LLM_PROVIDER` from `src/.env` (not the UI toggle).

**Local dev:** run the API (above) and, in a second terminal, `cd frontend && npm ci && npm run dev` — open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` and `/health` to the backend.

**Production:** build with `cd frontend && npm ci && npm run build`, then start uvicorn from the repo root; the API serves `frontend/dist` on the same port.

Full setup (EC2 remote API, env vars, test images): see [`frontend/README.md`](frontend/README.md).

## API Endpoints

| Endpoint | Method | Status | Description |
|---|---|---|---|
| `/health` | GET | Live | Service health check |
| `/api/analyze` | POST | Live | Score media authenticity (four signals → compliance status) |
| `/api/query` | POST | Live | Query RAG pipeline for regulation citations |
| `/api/issue` | POST | Live (503 until Sybol configured) | Score media → RAG citations → audit trail → submit to Sybol `businessLogic` API → return signed W3C VC 1.1. Returns 503 until `SYBOL_API_URL`, `SYBOL_ACCESS_TOKEN`, and `SYBOL_ID_TOKEN` are set. |

Interactive docs: `http://localhost:8000/docs`

## Score an image

### Option A — HTTP request (full API)

With the server running, upload any JPEG, PNG, or WebP file:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@/path/to/your/image.png"
```

Example response:

```json
{
  "authenticity_score": 0.64,
  "score_breakdown": { "m": 0.46, "a": 0.88, "v": 0.70, "p": 0.50 },
  "compliance_status": "review",
  "media_hash": "b26da027829d45fb153c23cc0cfe0a3300e077c98d53f534f6e9ec51f33beffb"
}
```

| Field | Meaning |
|---|---|
| `authenticity_score` | Overall score in `[0.0, 1.0]` |
| `score_breakdown` | `{ m, a, v, p }` — metadata, artifacts, visual, provenance |
| `compliance_status` | `compliant` (≥ 0.7), `review` (0.3–0.7), `non-compliant` (< 0.3) |
| `media_hash` | SHA-256 of the raw file before any processing |

### Option B — Python (scoring only, no Qdrant)

To test scoring without starting the API or connecting to Qdrant:

```bash
PYTHONPATH=src python3 -c "
from pathlib import Path
from scoring.pipeline import score_image

path = Path('path/to/your/image.png')
result = score_image(path.read_bytes(), filename=path.name, content_type='image/png')
print(result.model_dump_json(indent=2))
"
```

Replace `path/to/your/image.png` with your file path and set `content_type` to `image/jpeg` or `image/webp` as appropriate.

## Tests

```bash
poetry run pytest tests/unit/ --cov=src --cov-fail-under=80
poetry run pytest tests/integration/
```

## Branch Policy

All development happens on the `devel` branch. Do not push directly to `main`.
