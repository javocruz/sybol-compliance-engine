"""
Full local pipeline: score → RAG (Qdrant) → audit → Sybol signed VC.

Usage:
  # Qdrant running + ingest done; Sybol email/password in env
  QDRANT_URL=http://localhost:6333 QDRANT_API_KEY= \\
  SYBOL_EMAIL=... SYBOL_PASSWORD=... \\
  PYTHONPATH=src python3 -m scripts.sybol_e2e_full_issue \\
    qa/test_cases/golden/authentic/ar20.jpg
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import replace
from pathlib import Path

from src.api.dependencies import Settings, get_qdrant_client
from src.credentials.audit import write_audit_record
from src.credentials.catalog_issue_builder import build_catalog_issue_request
from src.credentials.sybol_catalog import ensure_media_compliance_catalog
from src.credentials.sybol_client import SybolClient, SybolSigningError
from src.rag.pipeline import load_index
from src.rag.query import query_regulations
from src.scoring.pipeline import score_image
from src.scoring.preprocess import ScoringError


def main() -> int:
    image_path = Path(
        sys.argv[1] if len(sys.argv) > 1 else "qa/test_cases/golden/authentic/ar20.jpg"
    )
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

    print(f"=== 1. Score {image_path.name} ===")
    try:
        result = score_image(content, filename=image_path.name, content_type=content_type)
    except ScoringError as exc:
        print(f"Scoring failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"  score={result.authenticity_score:.2f} "
        f"status={result.compliance_status.value}"
    )

    print("\n=== 2. RAG (Qdrant regulations index) ===")
    try:
        index, _ = load_index()
        rag_query = (
            f"What EU regulations apply to media with authenticity score "
            f"{result.authenticity_score:.2f} and compliance status "
            f"{result.compliance_status.value}?"
        )
        rag = query_regulations(rag_query, index)
        print(f"  refs={len(rag.regulation_refs)} summary={rag.summary[:120]}...")
        if rag.regulation_refs:
            ref = rag.regulation_refs[0]
            print(f"  top ref: {ref.regulation} {ref.article}")
    except Exception as exc:
        print(f"  RAG failed: {exc}", file=sys.stderr)
        return 1

    settings = Settings()
    qdrant = get_qdrant_client(settings)
    credential_id = f"urn:uuid:{uuid.uuid4()}"

    print("\n=== 3. Audit trail (Qdrant media_audit) ===")
    try:
        evidence_url = write_audit_record(
            result, rag, credential_id, qdrant, settings
        )
        print(f"  evidence_url={evidence_url}")
    except Exception as exc:
        print(f"  Audit failed: {exc}", file=sys.stderr)
        return 1

    print("\n=== 4. Sybol signed VC ===")
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
        timeout=max(settings.sybol_request_timeout, 90.0),
    )
    try:
        client.ensure_authenticated()
        doc_id = ensure_media_compliance_catalog(client)
        settings = replace(settings, sybol_document_id=doc_id)
        catalog_doc = client.get_catalog_document(doc_id)
        issue_request = build_catalog_issue_request(
            result,
            rag,
            settings=settings,
            evidence_url=evidence_url,
            catalog_document=catalog_doc,
        )
        signed = client.issue_credential(issue_request)
        print(f"  ISSUE OK jti={signed.get('jti')}")
        print(f"  credential_id={credential_id}")
        return 0
    except (ValueError, SybolSigningError) as exc:
        print(f"  Sybol failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
