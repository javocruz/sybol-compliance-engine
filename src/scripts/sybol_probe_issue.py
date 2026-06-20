"""
Test Sybol issuance after tokens are in src/.env or environment.

Usage:
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

from src.api.dependencies import Settings
from src.credentials.catalog_issue_builder import build_catalog_issue_request
from src.credentials.sybol_client import SybolClient, SybolSigningError
from src.rag.models import ComplianceResult, RegulationRef
from src.scoring.models import ComplianceStatus, ScoringResult, SignalBreakdown


def main() -> int:
    settings = Settings()
    client = SybolClient(
        api_base_url=settings.sybol_api_base_url,
        access_token=settings.sybol_access_token,
        id_token=settings.sybol_id_token,
        email=settings.sybol_email,
        password=settings.sybol_password,
        document_id=settings.sybol_document_id,
        issuer_key=settings.sybol_issuer_key,
        timeout=settings.sybol_request_timeout,
    )

    print("=== Auth ===")
    try:
        client.ensure_authenticated()
        print("  Authenticated OK")
    except SybolSigningError as exc:
        print(f"  FAILED: {exc}")
        print("  Tip: paste tokens from wallet DevTools into src/.env")
        return 1

    print("\n=== Catalog documents ===")
    try:
        docs = client.list_catalog_documents(search="media")
        if not docs:
            docs = client.list_catalog_documents()
        for d in docs[:15]:
            print(f"  {d.get('code') or d.get('name')}: id={d.get('id')}")
        if not settings.sybol_document_id:
            print("  Set SYBOL_DOCUMENT_ID from list above (or ask Iñigo for MediaCompliance doc)")
    except SybolSigningError as exc:
        print(f"  FAILED: {exc}")

    if not settings.sybol_document_id or not settings.sybol_issuer_key:
        print("\nSkipping issue probe — SYBOL_DOCUMENT_ID and SYBOL_ISSUER_KEY required.")
        return 2

    print("\n=== Issue probe (dry run payload) ===")
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
            result, rag, settings=settings, evidence_url="https://example.com/audit/demo"
        )
        print(json.dumps(req, indent=2)[:800])
        signed = client.issue_credential(req)
        print("\n  ISSUE OK")
        print(f"  keys in response: {list(signed.keys())}")
        return 0
    except ValueError as exc:
        print(f"  Config error: {exc}")
        return 2
    except SybolSigningError as exc:
        print(f"  Issue FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
