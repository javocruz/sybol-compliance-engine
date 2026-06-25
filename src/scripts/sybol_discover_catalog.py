"""
List catalog documents and tenant settings to find SYBOL_DOCUMENT_ID / SYBOL_ISSUER_KEY.

Usage:
  poetry run python -m scripts.sybol_discover_catalog
  poetry run python -m scripts.sybol_discover_catalog --search Media
"""

import argparse
import os
import sys

from src.credentials.sybol_client import SybolClient, SybolSigningError


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover Sybol catalog document IDs")
    parser.add_argument("--search", default="", help="Filter catalog documents by name")
    args = parser.parse_args()

    client = SybolClient(
        api_base_url=os.getenv(
            "SYBOL_API_BASE_URL", "https://api.develop.wallet.sybol.id"
        ),
        access_token=os.getenv("SYBOL_ACCESS_TOKEN"),
        id_token=os.getenv("SYBOL_ID_TOKEN"),
        email=os.getenv("SYBOL_EMAIL"),
        password=os.getenv("SYBOL_PASSWORD"),
    )

    try:
        client.ensure_authenticated()
        docs = client.list_catalog_documents(search=args.search or None)
    except SybolSigningError as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        return 1

    print("Catalog documents:")
    for doc in docs:
        print(
            f"  id={doc.get('id')}  name={doc.get('name')}  "
            f"format={doc.get('supported_format')}"
        )
        claims = doc.get("claims") or []
        if claims:
            keys = [c.get("key") for c in claims if isinstance(c, dict)]
            print(f"    claim keys: {keys}")

    if not docs:
        print("  (none — create MediaCompliance document in catalog or ask Sybol)")

    print("\nSet in src/.env:")
    print("  SYBOL_DOCUMENT_ID=<id from list above>")
    print("  SYBOL_ISSUER_KEY=<KMS key id from Sybol / wallet settings>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
