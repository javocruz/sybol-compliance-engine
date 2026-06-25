#!/usr/bin/env bash
# Cron-friendly health probe. Exit 0 when API + Qdrant are healthy.
# Example crontab: */5 * * * * /home/javier/sybol-compliance-engine/deploy/healthcheck.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${HEALTHCHECK_BASE_URL:-http://127.0.0.1:8000}"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

fail() {
  msg="$1"
  echo "HEALTHCHECK FAIL: $msg"
  if [[ -n "$SLACK_WEBHOOK" ]]; then
    curl -sf -X POST "$SLACK_WEBHOOK" \
      -H 'Content-Type: application/json' \
      -d "{\"text\":\"Sybol API healthcheck failed: $msg\"}" >/dev/null 2>&1 || true
  fi
  exit 1
}

curl -sf "$BASE_URL/health" >/dev/null || fail "API /health unreachable"
curl -sf "$BASE_URL/api/status" | grep -q '"api":"ok"' || fail "API /api/status not ok"
curl -sf http://127.0.0.1:6333/healthz >/dev/null || fail "Qdrant unhealthy"

echo "HEALTHCHECK OK $(date -u +%Y-%m-%dT%H:%M:%SZ)"
