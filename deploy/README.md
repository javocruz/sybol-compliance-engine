# EC2 Ceremony Deploy — `54.154.92.29`

Public demo URL (after SG port 8000 is open): **http://54.154.92.29:8000/**

## Pelayo — security group

Ask Pelayo to open **inbound TCP 8000** on the EC2 security group:

> Hola Pelayo — la nueva IP es **54.154.92.29**. SSH OK y disco ampliado, gracias. Para la ceremonia del AI Lab necesitamos el puerto **8000** abierto en el security group. ¿Lo podéis habilitar?

## Laptop → server (first time)

```bash
SSH_KEY=~/.ssh/sybol_ie_javier
HOST=javier@54.154.92.29

ssh -i $SSH_KEY $HOST 'git clone https://github.com/javocruz/sybol-compliance-engine.git || (cd sybol-compliance-engine && git pull)'
scp -i $SSH_KEY src/.env $HOST:~/sybol-compliance-engine/src/.env
ssh -i $SSH_KEY $HOST 'chmod 600 ~/sybol-compliance-engine/src/.env'
```

Ensure server `src/.env` includes:

```env
QDRANT_URL=http://127.0.0.1:6333
PUBLIC_BASE_URL=http://54.154.92.29:8000
```

## Bootstrap on server

```bash
ssh -i ~/.ssh/sybol_ie_javier javier@54.154.92.29
cd ~/sybol-compliance-engine && git pull && bash deploy/ec2-bootstrap.sh
```

## Frontend (laptop)

```bash
cd frontend && npm ci && VITE_API_BASE_URL= npm run build
rsync -avz -e "ssh -i ~/.ssh/sybol_ie_javier" dist/ \
  javier@54.154.92.29:~/sybol-compliance-engine/frontend/dist/
```

## Run API (tmux on server)

```bash
tmux new -s sybol-api
cd ~/sybol-compliance-engine && source .venv/bin/activate
set -a && source src/.env && set +a
export PYTHONPATH=src HF_HOME=$HOME/.cache/huggingface
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
# Ctrl+B, D to detach
```

## Smoke tests

```bash
BASE=http://54.154.92.29:8000
curl -s $BASE/health
curl -s $BASE/api/status | python3 -m json.tool
curl -s -X POST $BASE/api/analyze -F "file=@qa/test_cases/golden/authentic/ar20.jpg" | head -c 300
curl -s -X POST $BASE/api/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"What are AI-generated media disclosure rules?"}' | head -c 400
```

After `/api/issue`, confirm `evidenceUrl` is `http://54.154.92.29:8000/api/audit/<uuid>` and that URL returns JSON.

## Ceremony demo flow (~5 min)

1. `/api/status` — stack green
2. Analyze — AI image (0.26) vs authentic (~0.83)
3. Query — EU AI Act citation
4. Issue — signed VC
5. Sybol wallet — verified credential + clickable evidence link

## Rollback

```bash
tmux kill-session -t sybol-api
docker stop sybol-qdrant
```

Do **not** commit `deploy/ssh-keys-for-pelayo.txt` or `src/.env`.
