# src/credentials/ — Darius

Your job here is to take the unsigned VC payload from Javier and submit
it to Sybol's businessLogic API to get back a fully signed Verifiable Credential.

Before you can implement this, you need three things from Iñigo.
You are the one who reaches out to him for these — contact him directly:

1. The issuer DID value for Sybol
2. Confirmation that MEDIA_COMPLIANCE_CREDENTIAL is registered
   in the Sybol catalog schema
3. Whether the signing endpoint is /credentials/issue or a
   dedicated signing endpoint

Contact Iñigo at: inigo@sybol.id
Copy Javier on any technical questions so he stays in the loop.

While you are waiting for the above, scaffold the API call with
placeholder values so the structure is ready to plug in the moment
Iñigo confirms. The function signature, request format, error handling,
and response parsing should all be done — just swap in the real values.

Also make sure errors are surfaced clearly to the team.
If the Sybol API returns unexpected responses or schema mismatches,
log them in detail and flag in the WhatsApp group immediately.

# Darius — Credentials, Deployment, Railway & CI/CD

## Overview

My contribution focused on deployment infrastructure, environment integration, CI/CD automation, and preparation of the Sybol credential issuance pipeline.

The repository now includes:

* Railway deployment configuration
* Qdrant integration through environment variables
* Railway health checks
* Startup resilience when Qdrant is unavailable
* GitHub Actions CI pipeline
* Unit and integration test coverage
* Sybol credential signing client scaffolding
* Contract validation for signed credentials
* Documentation for automatic deployments from GitHub

---

# Tasks Completed

## Railway Deployment

The FastAPI service is configured for Railway using:

```toml
[deploy]
startCommand = "sh -c 'uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}'"
healthcheckPath = "/health"
restartPolicyType = "on_failure"
```

### Health Endpoint

```http
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

Railway uses this endpoint to determine deployment success.

---

## Qdrant Integration

The project uses Qdrant as the vector database backing the RAG subsystem.

### Required Environment Variables

```env
QDRANT_URL=http://<qdrant-host>:6333
QDRANT_API_KEY=<optional>
```

### Railway Setup

Qdrant is deployed as a separate Railway service:

```text
qdrant/qdrant
```

A persistent volume must be attached:

```text
/qdrant/storage
```

The FastAPI service communicates with Qdrant through Railway private networking.

---

## Startup Resilience

The FastAPI lifespan process was modified so that temporary Qdrant failures do not prevent deployment.

Benefits:

* Railway deployments remain healthy
* Health checks continue to pass
* The application can recover when Qdrant becomes available
* Dependency outages do not crash the API

---

# Sybol Credential Signing Integration

## Current Status

The integration has been scaffolded and is ready to connect to the production Sybol environment.

Implemented:

* Sybol API client
* Authentication support
* Error handling
* Response parsing
* Contract validation
* Unit test coverage

Relevant files:

```text
src/credentials/sybol_client.py
src/credentials/vc_builder.py
tests/unit/test_sybol_client.py
```

---

## Supported Validation

The Sybol client validates:

### Issuer DID

```text
issuer
```

### Credential Type

```text
MediaComplianceCredential
```

### Credential Schema

```text
credentialSchema
```

### Proof Section

```text
proof
```

Any mismatch generates a detailed exception and log entry.

---

## Pending Information from Sybol

The following values are still required before credential issuance can be fully enabled:

### Issuer DID

```env
SYBOL_EXPECTED_ISSUER_DID=
```

### Credential Schema Registration

Confirmation that:

```text
MEDIA_COMPLIANCE_CREDENTIAL
```

is registered in the Sybol catalog.

Required:

```env
SYBOL_CREDENTIAL_SCHEMA_ID=
```

### Signing Endpoint

Confirmation whether signing should occur through:

```text
/credentials/issue
```

or

```text
/api/bl/credentials
```

or another dedicated endpoint.

Required:

```env
SYBOL_API_URL=
```

### Authentication

Required values:

```env
SYBOL_ACCESS_TOKEN=
SYBOL_ID_TOKEN=
```

---

# CI Pipeline

GitHub Actions CI is configured through:

```text
.github/workflows/ci.yml
```

Current triggers:

```yaml
push:
  branches:
    - main

pull_request:
  branches:
    - main
```

The pipeline executes:

### Dependency Installation

```bash
poetry install --with dev
```

### Linting

```bash
poetry run ruff check --fix src tests
poetry run black src tests
```

### Type Checking

```bash
cd src && poetry run mypy .
```

### Testing

```bash
poetry run pytest -q --cov=src
```

Coverage threshold:

```text
80%
```

Current coverage exceeds the minimum requirement.

---

# Local Development

## Install Dependencies

```bash
poetry install --with dev
```

## Configure Environment

```bash
cp .env.example .env
```

Populate:

```env
QDRANT_URL=http://localhost:6333
MISTRAL_API_KEY=...
```

## Run API

```bash
PYTHONPATH=src poetry run uvicorn api.main:app --reload
```

Verify:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

---

# Railway Deployment Guide

## Initial Deployment

Install Railway CLI:

```bash
npm install -g @railway/cli
```

Login:

```bash
railway login
```

Deploy:

```bash
railway up
```

View logs:

```bash
railway logs
```

---

# Automatic Deployments from Main

## Prerequisites

The repository owner must:

1. Have admin access to the repository
2. Connect GitHub to Railway
3. Grant Railway GitHub App access
4. Connect the Railway service to the repository

---

## Configure Railway

Open:

```text
Service
    → Source
    → Connect Repo
```

Select:

```text
Repository: sybol-compliance-engine
```

Enable:

```text
Auto Deploy = ON
```

Set deployment branch:

```text
main
```

---

## Deployment Flow

```text
Developer
    ↓
Push to main
    ↓
GitHub Actions CI
    ↓
Tests Pass
    ↓
Railway Auto Deploy
    ↓
Production Environment
```

---

## Verifying Deployment

Health check:

```bash
curl https://<railway-domain>/health
```

Expected:

```json
{
  "status": "ok"
}
```

Inspect logs:

```bash
railway logs
```

No startup exceptions should appear.

---

# Repository Handover Notes

Before merging future work:

* Ensure all tests pass
* Ensure Qdrant service is running
* Ensure Railway environment variables are configured
* Ensure Railway is connected to GitHub
* Ensure Auto Deploy targets `main`
* Ensure Sybol environment variables are configured when available

The repository is deployment-ready.

The only remaining blocker for full credential issuance is receiving the final Sybol configuration values (issuer DID, schema registration, signing endpoint, and authentication credentials).