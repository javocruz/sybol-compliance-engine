#!/usr/bin/env bash
# Idempotent EC2 bootstrap for Sybol Compliance Engine (CPU, no GPU).
# Run on the server from repo root: bash deploy/ec2-bootstrap.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

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
curl -sf http://127.0.0.1:6333/healthz >/dev/null && echo "Qdrant OK" || { echo "Qdrant failed"; exit 1; }

echo "=== Python venv ==="
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
if ! python -c "import torch" 2>/dev/null; then
  pip install torch --index-url https://download.pytorch.org/whl/cpu
fi
if ! command -v poetry >/dev/null; then
  pip install poetry -q
fi
poetry export -f requirements.txt --without-hashes --only main -o /tmp/req.txt
grep -v '^torch==' /tmp/req.txt > /tmp/req-notorch.txt || true
pip install -r /tmp/req-notorch.txt -q

echo "=== Env ==="
if [[ ! -f src/.env ]]; then
  echo "Copy deploy/ec2.env.example to src/.env and fill secrets first."
  exit 1
fi
set -a && source src/.env && set +a
export PYTHONPATH=src HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"

echo "=== Ingest (if regulations collection missing) ==="
NEED_INGEST=1
if curl -sf "http://127.0.0.1:6333/collections/regulations" 2>/dev/null | grep -q '"status":"ok"'; then
  NEED_INGEST=0
  echo "regulations collection exists — skipping ingest"
fi
if [[ "$NEED_INGEST" -eq 1 ]]; then
  python3 -m scripts.ingest
fi

echo ""
echo "=== Bootstrap complete ==="
echo "Start API in tmux:"
echo "  tmux new -s sybol-api"
echo "  cd $ROOT && source .venv/bin/activate"
echo "  set -a && source src/.env && set +a"
echo "  export PYTHONPATH=src HF_HOME=\$HOME/.cache/huggingface"
echo "  python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
