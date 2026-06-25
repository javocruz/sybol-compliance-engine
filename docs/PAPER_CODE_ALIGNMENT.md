# Paper vs Code Alignment

Reference for reconciling research paper claims with the implementation (Jun 2026).

| Paper / slide claim | Code reality | Env / flag |
|---------------------|--------------|------------|
| Signal weights 0.30 / 0.30 / 0.20 / 0.20 | Default **0.18 / 0.22 / 0.15 / 0.45** (golden-calibrated) | `SIGNAL_WEIGHTS` JSON or `SIGNAL_WEIGHT_WM` etc. |
| Platt scaling enabled | **Off by default** | `PLATT_ENABLED=true` |
| W3C VC 2.0 | **VC 1.1** (`@context` …/2018/credentials/v1) | `vc_version` in `/api/status` |
| Hallucination guard drops unknown regulation | **Configurable** — default drops unknown regulation only; set `both` for article guard | `HALLUCINATION_GUARD_STRICTNESS` |
| Revocation supported | **Stub** — `POST /api/revoke/{vc_id}` sets `revoked` on audit record | Requires `API_KEYS` when set |
| Golden set 67 images | **77 images** (30 authentic / 37 AI / 10 edited) | `qa/test_cases/golden/` |
| RAG metrics published | Export via `python qa/rag_eval/export_metrics.py` → `qa/rag_eval/results.json` | Needs Qdrant + `MISTRAL_API_KEY` |
| Evidence URL public | `PUBLIC_BASE_URL` + `GET /api/audit/{id}` | `PUBLIC_BASE_URL` in `src/.env` |
| Test count ~122 | **173+** pytest tests; frontend vitest | CI on `main` |

## Recommended paper profile (optional reproduce)

```env
SIGNAL_WEIGHTS={"m":0.30,"a":0.30,"v":0.20,"p":0.20}
PLATT_ENABLED=false
```

Do not enable Platt without refitting — golden regression 77/77 assumes profile rules with raw weighted scores.
