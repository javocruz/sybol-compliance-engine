#!/usr/bin/env bash
# Idempotent EC2 bootstrap for Sybol Compliance Engine.
# Ubuntu minimal images lack python3-venv/pip — this script uses uv instead.
# Run on the server from repo root: bash deploy/ec2-bootstrap.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"

echo "=== uv (if missing) ==="
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi

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

echo "=== Python venv (uv) ==="
rm -rf .venv
uv venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
echo "Installing CPU torch (pinned)..."
uv pip install -r deploy/requirements-cpu.txt
uv pip install poetry poetry-plugin-export
poetry export -f requirements.txt --without-hashes --only main -o /tmp/req.txt
grep -v '^torch==' /tmp/req.txt > /tmp/req-notorch.txt || true
echo "Installing app dependencies..."
uv pip install -r /tmp/req-notorch.txt

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
  python -m scripts.ingest
fi

echo ""
echo "=== systemd (recommended) ==="
echo "  sudo cp deploy/sybol-api.service /etc/systemd/system/"
echo "  # Edit User/WorkingDirectory paths if not javier"
echo "  sudo systemctl daemon-reload && sudo systemctl enable --now sybol-api"
echo ""
echo "=== Bootstrap complete ==="
echo "Or start API in tmux (fallback):"
echo "  tmux new -s sybol-api"
echo "  cd $ROOT && source .venv/bin/activate"
echo "  set -a && source src/.env && set +a"
echo "  export PYTHONPATH=src HF_HOME=\$HOME/.cache/huggingface PATH=\$HOME/.local/bin:\$PATH"
echo "  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
