#!/usr/bin/env bash
# Check what's ready for the June 25 demo path.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ok() { echo "  [OK]   $1"; }
no() { echo "  [MISS] $1"; }

echo "=== Scoring demo (Option D) ==="
if [[ -d qa/test_cases/golden/authentic ]] && [[ $(ls qa/test_cases/golden/authentic 2>/dev/null | wc -l) -gt 0 ]]; then
  ok "Golden authentic images ($(ls qa/test_cases/golden/authentic | wc -l | tr -d ' '))"
else
  no "Golden authentic images"
fi
if [[ -d qa/test_cases/golden/ai_generated ]] && [[ $(ls qa/test_cases/golden/ai_generated 2>/dev/null | wc -l) -gt 0 ]]; then
  ok "Golden AI images ($(ls qa/test_cases/golden/ai_generated | wc -l | tr -d ' '))"
else
  no "Golden AI images"
fi
if [[ -f qa/test_cases/golden/manifest.json ]]; then ok "manifest.json"; else no "manifest.json"; fi

echo ""
echo "=== RAG (Option F) ==="
pdfs=(eu_ai_act gdpr espr_dpp lopdgdd ley_13_2022)
pdf_ok=0
for p in "${pdfs[@]}"; do
  if compgen -G "research/regulations/${p}*" > /dev/null; then ((pdf_ok++)) || true; fi
done
if [[ $pdf_ok -eq 5 ]]; then ok "All 5 regulation PDFs"; else no "Regulation PDFs ($pdf_ok/5 in research/regulations/)"; fi
if curl -sf http://localhost:6333/ >/dev/null 2>&1 || curl -sf http://127.0.0.1:6333/ >/dev/null 2>&1; then
  ok "Qdrant reachable on :6333"
else
  no "Qdrant on :6333 (run: docker run -p 6333:6333 qdrant/qdrant)"
fi
if [[ -f src/.env ]] && grep -q 'MISTRAL_API_KEY=.\+' src/.env 2>/dev/null; then ok "MISTRAL_API_KEY in src/.env"; else no "MISTRAL_API_KEY in src/.env"; fi

echo ""
echo "=== Sybol signing (Option A/C) ==="
if [[ -f src/.env ]]; then
  grep -q 'SYBOL_ACCESS_TOKEN=.\+' src/.env 2>/dev/null && ok "SYBOL_ACCESS_TOKEN set" || no "SYBOL_ACCESS_TOKEN (paste from browser DevTools)"
  grep -q 'SYBOL_ID_TOKEN=.\+' src/.env 2>/dev/null && ok "SYBOL_ID_TOKEN set" || no "SYBOL_ID_TOKEN"
  grep -q 'SYBOL_DOCUMENT_ID=.\+' src/.env 2>/dev/null && ok "SYBOL_DOCUMENT_ID set" || no "SYBOL_DOCUMENT_ID (ask Iñigo / discover catalog)"
  grep -q 'SYBOL_ISSUER_KEY=.\+' src/.env 2>/dev/null && ok "SYBOL_ISSUER_KEY set" || no "SYBOL_ISSUER_KEY (ask Iñigo)"
else
  no "src/.env (copy from src/.env.example)"
fi

echo ""
echo "Run: PYTHONPATH=src uvicorn src.api.main:app --reload --port 8000"
