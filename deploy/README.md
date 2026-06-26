# EC2 Deploy Runbook

Public demo URL: **http://54.154.92.29:8000/** (or HTTPS via Caddy — see below)

## Pelayo — infrastructure checklist

1. **Elastic IP** — attach to instance so IP survives reboot
2. **Security group** — inbound TCP 8000 (HTTP demo) and 443 (HTTPS when Caddy enabled)
3. **Optional DNS** — `compliance.sybol.id` → Elastic IP

## First-time bootstrap

```bash
SSH_KEY=~/.ssh/sybol_ie_javier
HOST=javier@54.154.92.29

ssh -i $SSH_KEY $HOST 'git clone https://github.com/javocruz/sybol-compliance-engine.git || (cd sybol-compliance-engine && git pull)'
scp -i $SSH_KEY src/.env $HOST:~/sybol-compliance-engine/src/.env
ssh -i $SSH_KEY $HOST 'chmod 600 ~/sybol-compliance-engine/src/.env'
ssh -i $SSH_KEY $HOST 'cd ~/sybol-compliance-engine && bash deploy/ec2-bootstrap.sh'
```

Copy [`deploy/ec2.env.example`](ec2.env.example) to `src/.env` and set secrets. Never commit `src/.env` or `deploy/ssh-keys-for-pelayo.txt`.

## systemd (recommended over tmux)

Requires sudo on the EC2 instance. If sudo is blocked, ask Pelayo or use tmux until access is granted.

```bash
sudo cp deploy/sybol-api.service /etc/systemd/system/
# Edit User/WorkingDirectory if paths differ (default: javier, ~/sybol-compliance-engine)
sudo systemctl daemon-reload
sudo systemctl enable --now sybol-api
sudo systemctl status sybol-api
sudo journalctl -u sybol-api -f
```

Retire tmux after systemd is live:

```bash
tmux kill-session -t sybol-api 2>/dev/null || true
```

Reboot test: `sudo reboot` — API should auto-start; Qdrant container restarts via Docker.

The service binds to `127.0.0.1:8000`. Use Caddy for public HTTPS on 443.

## HTTPS with Caddy

```bash
sudo apt install -y caddy
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
# Set PUBLIC_BASE_URL=https://compliance.sybol.id in src/.env
sudo systemctl reload caddy
```

Security headers (HSTS, X-Content-Type-Options, etc.) are configured in [`deploy/Caddyfile`](Caddyfile).

## Deploy updates

On server:

```bash
cd ~/sybol-compliance-engine && bash deploy/deploy.sh
```

When systemd is not installed, `deploy.sh` calls [`deploy/start-api-tmux.sh`](start-api-tmux.sh) to restart the API with `src/.env` loaded.

Manual restart only:

```bash
bash deploy/start-api-tmux.sh
```

Flags: `--skip-ingest`, `--skip-frontend`

Frontend (from laptop):

```bash
cd frontend && npm ci && VITE_API_BASE_URL= npm run build
rsync -avz -e "ssh -i ~/.ssh/sybol_ie_javier" dist/ \
  javier@54.154.92.29:~/sybol-compliance-engine/frontend/dist/
```

## CPU-only PyTorch

[`deploy/requirements-cpu.txt`](requirements-cpu.txt) pins CPU torch before Poetry export. Bootstrap and deploy scripts use this to avoid CUDA wheels on EC2.

## Qdrant persistence

Named volume `sybol_qdrant_data` survives container restarts. Do not `docker rm -v sybol-qdrant` unless re-ingesting.

## Secrets management

### Short term

- `chmod 600 src/.env` on the server (never commit `src/.env`)
- API keys for write endpoints: set `API_KEYS=<comma-separated-keys>` in `src/.env`
- Demo operators pass `X-API-Key` header on `/api/issue` and `/api/revoke` only (`/api/analyze` and `/api/query` stay open)
- Frontend build: set `VITE_API_KEY` when issuing from the UI against a keyed server

```bash
openssl rand -hex 32   # generate a demo key
curl -X POST http://54.154.92.29:8000/api/issue \
  -H "X-API-Key: $KEY" -F "file=@qa/test_cases/golden/authentic/ar20.jpg"
```

### Medium term — AWS SSM Parameter Store

Store production secrets under `/sybol/compliance/*` (one parameter per env var):

| Parameter path | Example value |
|----------------|---------------|
| `/sybol/compliance/MISTRAL_API_KEY` | `sk-…` |
| `/sybol/compliance/SYBOL_ACCESS_TOKEN` | `…` |
| `/sybol/compliance/API_KEYS` | `hex-key-1,hex-key-2` |
| `/sybol/compliance/PUBLIC_BASE_URL` | `https://compliance.sybol.id` |

IAM: instance role needs `ssm:GetParametersByPath` on `arn:aws:ssm:REGION:ACCOUNT:parameter/sybol/compliance/*`.

On deploy or boot, pull into `src/.env`:

```bash
aws ssm get-parameters-by-path --path /sybol/compliance --with-decryption \
  --query 'Parameters[*].[Name,Value]' --output text | while read -r name value; do
  key=$(basename "$name")
  echo "$key=$value" >> src/.env
done
chmod 600 src/.env
```

Optional: extend `deploy/deploy.sh` to run this block when `USE_SSM_SECRETS=1` is set. Rotate keys in SSM and redeploy — no secrets in git or plaintext on laptops.

## Monitoring

```bash
chmod +x deploy/healthcheck.sh
```

See [`deploy/cron-healthcheck.example`](cron-healthcheck.example) for a crontab line (every 5 minutes).

Set `SLACK_WEBHOOK_URL` in `src/.env` for failure alerts.

## Audit trail immutability

Audit records live in Qdrant `media_audit` collection (metadata only, no image bytes). For production:

- Restrict Qdrant to localhost (already `127.0.0.1:6333`)
- Use Qdrant API key + network isolation
- For stronger guarantees, mirror audit writes to S3 with Object Lock (write-once)

Revocation updates the audit payload `revoked` flag — it does not delete history.

## Smoke tests

```bash
BASE=http://54.154.92.29:8000
curl -s $BASE/health
curl -s $BASE/api/status | python3 -m json.tool
curl -s -X POST $BASE/api/analyze -F "file=@qa/test_cases/golden/authentic/ar20.jpg" | head -c 300
```

## Rollback

```bash
git checkout <previous-commit>
bash deploy/deploy.sh --skip-ingest
```

Or: `sudo systemctl stop sybol-api`

## Ceremony demo flow

1. `/api/status` — stack green
2. Analyze — AI image vs authentic
3. Query — EU AI Act citation
4. Issue — signed VC + evidence URL
5. Verify — `GET /api/verify/{vc_id}` (audit trail; optional revoke + re-verify)
6. Sybol wallet — verify credential
