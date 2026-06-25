# Sybol Compliance Engine — Project Status

**Last updated:** 26 June 2026  
**Live demo:** http://54.154.92.29:8000/  
**Repository:** `main`

---

## Executive summary

| Area | Status |
|------|--------|
| Scoring pipeline | **Done** — 77/77 golden regression; env-configurable weights |
| RAG engine | **Done** — 5 PDFs, TC-005 passed; metrics export script |
| VC issuance | **Done** — Sybol-signed on develop; verify/revoke stubs |
| EC2 deploy | **Done** — Qdrant + API + bundled UI |
| Frontend | **Done** — Sybol-branded UI, System status tab |
| CI | **Done** — pytest + frontend build/test + audit scans |

---

## Key endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/status` | Stack health (chunks, model, Sybol, git commit) |
| `POST /api/analyze` | Authenticity scoring |
| `POST /api/query` | Regulation RAG |
| `POST /api/issue` | Signed VC + audit trail |
| `GET /api/audit/{id}` | Public evidence JSON |
| `GET /api/verify/{id}` | Validity + revocation check |
| `POST /api/revoke/{id}` | Mark credential revoked |

---

## Scoring configuration

| Setting | Default | Notes |
|---------|---------|-------|
| Weights | 0.18 / 0.22 / 0.15 / 0.45 | Paper profile via `SIGNAL_WEIGHTS` |
| Platt | Off | `PLATT_ENABLED=true` |
| VC version | 1.1 | See `docs/PAPER_CODE_ALIGNMENT.md` |

---

## QA status

| TC | Status |
|----|--------|
| TC-001 | Pass (30/30 authentic) |
| TC-002 | Pass (37/37 AI) |
| TC-003 | Pass (10/10 edited) |
| TC-004 | Pass |
| TC-005 | Pass (live RAG metrics) |
| TC-006 | Pass (VC 1.1 schema) |

---

## Deploy

See [`deploy/README.md`](../deploy/README.md) for systemd, Caddy HTTPS, and `deploy/deploy.sh`.

---

## References

- [`NOTES_FOR_ALEX.md`](../NOTES_FOR_ALEX.md)
- [`docs/PAPER_CODE_ALIGNMENT.md`](./PAPER_CODE_ALIGNMENT.md)
- [`qa/QA_LOG.md`](../qa/QA_LOG.md)
