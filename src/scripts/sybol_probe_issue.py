"""Test Sybol issuance after tokens are in src/.env or environment.

Usage:
  export SYBOL_EMAIL=... SYBOL_PASSWORD=...
  export SYBOL_DOCUMENT_ID=...   # optional — defaults to PRUEBA22 on develop
  PYTHONPATH=src python3 -m scripts.sybol_probe_issue
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Load src/.env if present (simple parse, no dotenv dep required)
_env = Path(__file__).resolve().parents[1] / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from dataclasses import replace

from src.api.dependencies import Settings
from src.credentials.catalog_issue_builder import build_catalog_issue_request
from src.credentials.sybol_client import SybolClient, SybolSigningError
from src.rag.models import ComplianceResult, RegulationRef
from src.scoring.models import ComplianceStatus, ScoringResult, SignalBreakdown

# Active develop catalog doc (Documento de prueba) — used when SYBOL_DOCUMENT_ID unset
DEFAULT_PROBE_DOCUMENT_ID = "a4236879-fcfd-4bc0-8811-e2ccf873fb70"


def main() -> int:
    settings = Settings()
    document_id = settings.sybol_document_id or DEFAULT_PROBE_DOCUMENT_ID
    if not os.getenv("SYBOL_DOCUMENT_ID"):
        print(f"SYBOL_DOCUMENT_ID unset — using develop probe doc {document_id}")
        settings = replace(settings, sybol_document_id=document_id)

    client = SybolClient(
        api_base_url=settings.sybol_api_base_url,
        access_token=settings.sybol_access_token,
        id_token=settings.sybol_id_token,
        email=settings.sybol_email,
        password=settings.sybol_password,
        document_id=document_id,
        issuer_key=settings.sybol_issuer_key,
        cognito_client_id=settings.sybol_cognito_client_id,
        cognito_region=settings.sybol_cognito_region,
        timeout=settings.sybol_request_timeout,
    )

    print("=== Auth ===")
    try:
        client.ensure_authenticated()
        print("  Authenticated OK (Cognito + role-claim fix if needed)")
    except SybolSigningError as exc:
        print(f"  FAILED: {exc}")
        return 1

    print("\n=== Catalog documents (media search) ===")
    try:
        docs = client.list_catalog_documents(search="media")
        if not docs:
            docs = client.list_catalog_documents()
        for d in docs[:10]:
            code = d.get("code") or d.get("name")
            print(f"  {code}: id={d.get('id')} state={d.get('state')}")
        if not any("media" in str(d.get("code", "")).lower() for d in docs):
            print("  (no MediaCompliance doc — requesting one via backoffice)")
            try:
                resp = client.request_catalog_document(
                    name="Media Compliance Credential",
                    description=(
                        "Verifiable credential for image authenticity and "
                        "EU regulatory compliance (mediaHash, score, regulationRefs)."
                    ),
                    justification="IEU Labs compliance engine demo — June 2026",
                )
                print(f"  document-request response: {json.dumps(resp)[:300]}")
            except SybolSigningError as exc:
                print(f"  document-request failed: {exc}")
    except SybolSigningError as exc:
        print(f"  catalog list FAILED: {exc}")

    if not settings.sybol_issuer_key:
        print("\nSkipping issue probe — SYBOL_ISSUER_KEY required.")
        return 2

    print("\n=== Catalog document schema ===")
    try:
        catalog_doc = client.get_catalog_document(document_id)
        claim_keys = [
            c.get("key") for c in (catalog_doc.get("claims") or []) if isinstance(c, dict)
        ]
        print(f"  doc={catalog_doc.get('code')} claims={claim_keys}")
    except SybolSigningError as exc:
        print(f"  FAILED: {exc}")
        catalog_doc = {}

    print("\n=== Issue probe ===")
    result = ScoringResult(
        authenticity_score=0.86,
        score_breakdown=SignalBreakdown(m=0.9, a=0.8, v=0.85, p=0.9),
        compliance_status=ComplianceStatus.COMPLIANT,
        media_hash="a" * 64,
        model_version="demo-probe",
    )
    rag = ComplianceResult(
        summary="Demo probe — EU AI Act transparency may apply.",
        regulation_refs=[
            RegulationRef(
                regulation="EU AI Act",
                article="Article 50",
                source_url="https://eur-lex.europa.eu/eli/reg/2024/1689",
                excerpt="Synthetic content disclosure.",
            )
        ],
    )
    try:
        req = build_catalog_issue_request(
            result,
            rag,
            settings=settings,
            evidence_url="https://example.com/audit/demo",
            catalog_document=catalog_doc or None,
        )
        print(json.dumps(req, indent=2)[:1000])
        signed = client.issue_credential(req)
        print("\n  ISSUE OK")
        print(f"  jti={signed.get('jti')}")
        print(f"  signed_token prefix={str(signed.get('signed_token', ''))[:60]}...")
        return 0
    except ValueError as exc:
        print(f"  Config error: {exc}")
        return 2
    except SybolSigningError as exc:
        print(f"  Issue FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
