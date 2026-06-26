#!/usr/bin/env bash
# Start or restart the API in tmux (fallback when systemd is not installed).
# Sources src/.env so MISTRAL_API_KEY and PUBLIC_BASE_URL are always loaded.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f src/.env ]]; then
  echo "src/.env missing — copy from deploy/ec2.env.example" >&2
  exit 1
fi

export GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"

tmux kill-session -t sybol-api 2>/dev/null || true

tmux new-session -d -s sybol-api \
  "cd '$ROOT' && set -a && source src/.env && set +a \
   && source .venv/bin/activate \
   && export PYTHONPATH=src GIT_COMMIT='$GIT_COMMIT' HF_HOME='$HF_HOME' \
   && exec python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"

echo "Waiting for API (commit=$GIT_COMMIT)..."
for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "API ready at http://127.0.0.1:8000"
    exit 0
  fi
  sleep 2
done

echo "API failed to become healthy within 120s" >&2
tmux capture-pane -t sybol-api -p 2>/dev/null | tail -20 >&2 || true
exit 1
