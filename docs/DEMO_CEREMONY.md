# Demo Ceremony Script

Live demo flow for the Sybol Compliance Engine. Target URL: **http://54.154.92.29:8000/** (HTTPS: `https://compliance.sybol.id` once Caddy is live).

## Pre-flight (5 min before audience)

1. Open the UI — confirm Sybol branding (Satoshi, teal header, System tab).
2. **System tab** — check `/api/status`: `api: ok`, `model_loaded: true`, `regulations_chunks > 0`.
3. Have two images ready:
   - Authentic: `qa/test_cases/golden/authentic/ar20.jpg`
   - AI-generated: any known synthetic sample from the golden set
4. If `API_KEYS` is set on the server, ensure the frontend was built with `VITE_API_KEY` or use curl with `X-API-Key` for Issue.

## Ceremony beats (~15 min)

### 1. System health (30 s)

- Show **System** tab: Qdrant, RAG index, model, git commit, uptime.
- Talking point: single EC2 stack — scoring model, RAG over EU AI Act chunks, Sybol wallet integration.

### 2. Analyze — authentic vs AI (3 min)

- **Analyze tab** — upload authentic image → high authenticity score, `compliant` or `review`.
- Upload AI image → lower score, `non-compliant` or `review`.
- Expand score breakdown (M/A/V/P signals).
- Talking point: multimodal scoring pipeline, no credential issued yet — read-only analysis.

### 3. Query regulations (2 min)

- **Query tab** — ask: *"What does the EU AI Act require for transparency of AI-generated content?"*
- Show answer + regulation citations with links.
- Talking point: RAG over ingested regulation chunks, not hallucinated statutes.

### 4. Issue credential (3 min)

- **Issue tab** — upload the same authentic image used in Analyze.
- Show signed VC card: compliance badge, authenticity gauge, regulation refs.
- **Evidence URL** — open in new tab → `/api/audit/{uuid}` JSON audit record.
- **Audit verification** row auto-loads: should show **Valid** with `audit_found: yes`.
- Optional: copy VC JSON or download for wallet import.

### 5. Verify (1 min)

- Point to the **Audit verification** badge on the Issue results panel (calls `GET /api/verify/{vc_id}`).
- Or from terminal:

```bash
curl -s http://54.154.92.29:8000/api/verify/<vc_id> | python3 -m json.tool
```

- Expected: `"valid": true`, `"revoked": false`, `"audit_found": true`.
- Talking point: audit-trail verification in Qdrant — not on-chain signature verification yet.

### 6. Optional revoke beat (2 min)

- Only if demonstrating revocation lifecycle:

```bash
curl -X POST http://54.154.92.29:8000/api/revoke/<vc_id> \
  -H "X-API-Key: $API_KEY"
```

- Re-call verify → `"valid": false`, `"revoked": true`.
- Refresh Issue results or re-fetch verify in UI → badge shows **Revoked**.

### 7. Sybol wallet (2 min)

- Import issued VC into Sybol wallet (if configured).
- Confirm credential displays; evidence URL resolves (HTTPS preferred for wallet deep links).

## Fallbacks

| Problem | Action |
|---------|--------|
| Model cold start slow | `WARMUP_ON_START=true` in server `.env`; wait for System tab `model_loaded` |
| Issue 401 | Missing `X-API-Key` — set `VITE_API_KEY` at build or pass header in curl |
| Evidence URL wrong host | Fix `PUBLIC_BASE_URL` in `src/.env`, restart API |
| Qdrant down | `docker start sybol-qdrant`; re-check `/api/status` |

## Post-demo

- Do not revoke production demo credentials unless rehearsing revoke beat.
- Check `journalctl -u sybol-api` or tmux logs for errors.
