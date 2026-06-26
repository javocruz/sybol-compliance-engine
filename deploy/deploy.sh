#!/usr/bin/env bash
# Idempotent deploy on EC2. Run from repo root on the server.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SKIP_INGEST=0
SKIP_FRONTEND=0
for arg in "$@"; do
  case "$arg" in
    --skip-ingest) SKIP_INGEST=1 ;;
    --skip-frontend) SKIP_FRONTEND=1 ;;
  esac
done

export PATH="${HOME}/.local/bin:${PATH}"

echo "=== git pull ==="
git pull --ff-only

echo "=== Python deps ==="
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || {
  uv venv .venv
  source .venv/bin/activate
}
uv pip install -r deploy/requirements-cpu.txt
uv pip install poetry poetry-plugin-export
poetry export -f requirements.txt --without-hashes --only main -o /tmp/req.txt
grep -v '^torch==' /tmp/req.txt > /tmp/req-notorch.txt || true
uv pip install -r /tmp/req-notorch.txt

echo "=== Qdrant ==="
if docker ps -a --format '{{.Names}}' | grep -qx sybol-qdrant; then
  docker start sybol-qdrant 2>/dev/null || true
else
  docker run -d --name sybol-qdrant --restart unless-stopped \
    -p 127.0.0.1:6333:6333 \
    -v sybol_qdrant_data:/qdrant/storage \
    qdrant/qdrant
fi
sleep 2
curl -sf http://127.0.0.1:6333/healthz >/dev/null || { echo "Qdrant failed"; exit 1; }

if [[ "$SKIP_INGEST" -eq 0 ]]; then
  set -a && source src/.env && set +a
  export PYTHONPATH=src HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
  if ! curl -sf "http://127.0.0.1:6333/collections/regulations" 2>/dev/null | grep -q '"status":"ok"'; then
    echo "=== ingest ==="
    python -m scripts.ingest
  fi
fi

if [[ "$SKIP_FRONTEND" -eq 0 ]] && [[ -d frontend/dist ]]; then
  echo "=== frontend dist present (build locally and rsync, or npm ci && npm run build here) ==="
fi

export GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

echo "=== restart API ==="
if systemctl is-active --quiet sybol-api 2>/dev/null; then
  sudo systemctl restart sybol-api
else
  echo "sybol-api.service not active — starting via tmux"
  bash deploy/start-api-tmux.sh
fi

echo "=== smoke ==="
sleep 2
curl -sf http://127.0.0.1:8000/health
curl -sf http://127.0.0.1:8000/api/status | head -c 200
echo ""
echo "Deploy complete (commit=$GIT_COMMIT)"
