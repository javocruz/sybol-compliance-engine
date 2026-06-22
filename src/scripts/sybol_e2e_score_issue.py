"""
Score a golden image and issue a Media Compliance VC on Sybol develop.

Bypasses Qdrant/RAG — uses a static regulation summary for pipeline testing.

Usage:
  export SYBOL_EMAIL=... SYBOL_PASSWORD=...
  PYTHONPATH=src python3 -m scripts.sybol_e2e_score_issue \\
    qa/test_cases/golden/authentic/ar20.jpg
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

from src.api.dependencies import Settings
from src.credentials.catalog_issue_builder import build_catalog_issue_request
from src.credentials.sybol_catalog import ensure_media_compliance_catalog
from src.credentials.sybol_client import SybolClient, SybolSigningError
from src.rag.models import ComplianceResult, RegulationRef
from src.scoring.pipeline import score_image
from src.scoring.preprocess import ScoringError


def main() -> int:
    image_path = Path(sys.argv[1] if len(sys.argv) > 1 else "qa/test_cases/golden/authentic/ar20.jpg")
    if not image_path.is_file():
        print(f"Image not found: {image_path}", file=sys.stderr)
        return 1

    content = image_path.read_bytes()
    suffix = image_path.suffix.lower()
    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")

    print(f"=== Score {image_path.name} ===")
    try:
        result = score_image(content, filename=image_path.name, content_type=content_type)
    except ScoringError as exc:
        print(f"Scoring failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"  score={result.authenticity_score:.2f} "
        f"status={result.compliance_status.value} "
        f"hash={result.media_hash[:16]}..."
    )

    rag = ComplianceResult(
        summary=(
            f"Static probe summary for {image_path.name}: authenticity "
            f"{result.authenticity_score:.2f}, status {result.compliance_status.value}."
        ),
        regulation_refs=[
            RegulationRef(
                regulation="EU AI Act",
                article="Article 50",
                source_url="https://eur-lex.europa.eu/eli/reg/2024/1689",
                excerpt="Transparency for AI-generated content.",
            )
        ],
    )

    settings = Settings()
    client = SybolClient(
        api_base_url=settings.sybol_api_base_url,
        access_token=settings.sybol_access_token,
        id_token=settings.sybol_id_token,
        email=settings.sybol_email,
        password=settings.sybol_password,
        document_id=settings.sybol_document_id,
        issuer_key=settings.sybol_issuer_key,
        cognito_client_id=settings.sybol_cognito_client_id,
        cognito_region=settings.sybol_cognito_region,
        timeout=max(settings.sybol_request_timeout, 60.0),
    )

    print("\n=== Sybol auth + catalog ===")
    try:
        client.ensure_authenticated()
        doc_id = ensure_media_compliance_catalog(client)
        settings = replace(settings, sybol_document_id=doc_id)
        catalog_doc = client.get_catalog_document(doc_id)
        print(f"  document={catalog_doc.get('code')} id={doc_id} state={catalog_doc.get('state')}")
    except SybolSigningError as exc:
        print(f"  FAILED: {exc}", file=sys.stderr)
        return 1

    print("\n=== Issue Media Compliance VC ===")
    try:
        req = build_catalog_issue_request(
            result,
            rag,
            settings=settings,
            evidence_url=f"file://{image_path.resolve()}",
            catalog_document=catalog_doc,
        )
        print(json.dumps({**req, "claims": {k: v[:40] + "..." if len(v) > 40 else v for k, v in req["claims"].items()}}, indent=2))
        signed = client.issue_credential(req)
        print("\n  ISSUE OK")
        print(f"  jti={signed.get('jti')}")
        print(f"  types in VC: MEDIA_COMPLIANCE_IE")
        return 0
    except (ValueError, SybolSigningError) as exc:
        print(f"  FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
