"""
Probe Sybol hosts and APIs to discover base URL, auth, catalog, and issuance format.

Usage (credentials from env only — never commit):
  export SYBOL_EMAIL=...
  export SYBOL_PASSWORD=...
  PYTHONPATH=src python3 -m scripts.sybol_probe
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

HOSTS = [
    "https://api.develop.wallet.sybol.id",
    "https://api.sybol.io",
    "https://api.sybol.id",
]

LOGIN_PATHS = [
    "/api/bl/auth/login",
    "/api/bo/auth/login",
    "/auth/login",
    "/api/auth/login",
]
TIMEOUT = 20.0


def _short(text: str, n: int = 300) -> str:
    text = text.replace("\n", " ")
    return text[:n] + ("..." if len(text) > n else "")


def try_login(base: str, path: str, email: str, password: str) -> dict[str, Any]:
    url = f"{base.rstrip('/')}{path}"
    try:
        r = httpx.post(
            url,
            json={"email": email, "password": password},
            timeout=TIMEOUT,
        )
    except httpx.RequestError as exc:
        return {"url": url, "ok": False, "error": str(exc)}

    body: Any = None
    try:
        body = r.json()
    except Exception:
        body = r.text[:500]

    tokens = {}
    if isinstance(body, dict):
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        if isinstance(data, dict):
            tokens = {
                "accessToken": bool(data.get("accessToken")),
                "idToken": bool(data.get("idToken")),
                "refreshToken": bool(data.get("refreshToken")),
            }

    return {
        "url": url,
        "status": r.status_code,
        "ok": r.is_success and tokens.get("accessToken") and tokens.get("idToken"),
        "tokens": tokens,
        "challenge": body.get("challengeName") if isinstance(body, dict) else None,
        "body_preview": _short(json.dumps(body) if not isinstance(body, str) else body),
    }


def extract_tokens(body: dict) -> tuple[str | None, str | None]:
    data = body.get("data")
    if not isinstance(data, dict):
        return None, None
    access = data.get("accessToken")
    id_token = data.get("idToken")
    return (
        access if isinstance(access, str) else None,
        id_token if isinstance(id_token, str) else None,
    )


def authed_get(base: str, path: str, access: str, id_token: str) -> dict[str, Any]:
    url = f"{base.rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {access}",
        "X-Id-Token": id_token,
        "x-id-token": id_token,
    }
    try:
        r = httpx.get(url, headers=headers, timeout=TIMEOUT)
    except httpx.RequestError as exc:
        return {"url": url, "ok": False, "error": str(exc)}

    try:
        body = r.json()
    except Exception:
        body = r.text[:800]

    preview = body
    if isinstance(body, dict) and "data" in body:
        data = body["data"]
        if isinstance(data, list):
            preview = {"success": body.get("success"), "data_count": len(data), "sample": data[:2]}
        elif isinstance(data, dict):
            preview = {"success": body.get("success"), "data_keys": list(data.keys())[:20]}

    return {
        "url": url,
        "status": r.status_code,
        "ok": r.is_success,
        "preview": preview,
    }


def probe_issue_formats(
    base: str, access: str, id_token: str, document_id: str | None, issuer_key: str | None
) -> list[dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {access}",
        "X-Id-Token": id_token,
        "Content-Type": "application/json",
    }
    url = f"{base.rstrip('/')}/api/bl/credentials"
    results = []

    catalog_body = {
        "documentId": document_id or "00000000-0000-4000-8000-000000000001",
        "issuerKey": issuer_key or "probe-key",
        "subject": "urn:media:probe000000000000000000000000000000000000000000000000000000",
        "claims": [
            {"key": "mediaHash", "value": "probe"},
            {"key": "authenticityScore", "value": "0.5"},
            {"key": "complianceStatus", "value": "review"},
        ],
        "format": "w3c-vc",
    }
    raw_vc_body = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "id": "urn:uuid:00000000-0000-4000-8000-000000000099",
        "type": ["VerifiableCredential", "MediaComplianceCredential"],
        "issuanceDate": "2026-06-20T12:00:00Z",
        "credentialSubject": {
            "id": "urn:media:probe",
            "mediaHash": "probe",
            "authenticityScore": 0.5,
            "complianceStatus": "review",
        },
    }

    for label, payload in [("catalog_v4", catalog_body), ("raw_w3c_vc", raw_vc_body)]:
        try:
            r = httpx.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        except httpx.RequestError as exc:
            results.append({"format": label, "ok": False, "error": str(exc)})
            continue
        try:
            body = r.json()
        except Exception:
            body = r.text[:500]
        results.append(
            {
                "format": label,
                "status": r.status_code,
                "ok": r.is_success,
                "preview": _short(json.dumps(body) if not isinstance(body, str) else body, 400),
            }
        )
    return results


def main() -> int:
    email = os.getenv("SYBOL_EMAIL")
    password = os.getenv("SYBOL_PASSWORD")
    if not email or not password:
        print("Set SYBOL_EMAIL and SYBOL_PASSWORD.", file=sys.stderr)
        return 1

    print("\n=== 1. Login probe (base URL + path) ===\n")
    print("  (Public catalog works without login — fetching develop catalog...)\n")
    try:
        r = httpx.get(f"{HOSTS[0]}/api/catalog/documents?limit=5", timeout=TIMEOUT)
        if r.is_success:
            n = len(r.json().get("data", []))
            print(f"  [OK] GET {HOSTS[0]}/api/catalog/documents -> {n}+ docs (no auth)\n")
    except Exception:
        pass

    print("  Login attempts:\n")
    winners: list[tuple[str, str, str, str]] = []
    for host in HOSTS:
        for path in LOGIN_PATHS:
            result = try_login(host, path, email, password)
            flag = "OK" if result.get("ok") else result.get("status", result.get("error"))
            print(f"  [{flag}] {result['url']}")
            if result.get("challenge"):
                print(f"       challenge: {result['challenge']}")
            if not result.get("ok") and result.get("body_preview"):
                print(f"       {result['body_preview']}")
            if result.get("ok"):
                r = httpx.post(
                    result["url"],
                    json={"email": email, "password": password},
                    timeout=TIMEOUT,
                )
                access, id_token = extract_tokens(r.json())
                if access and id_token:
                    winners.append((host, path, access, id_token))

    if not winners:
        print("\nNo successful login. Cannot probe catalog or issuance.")
        print("Try: VPN, different network, or credentials may target another environment.")
        return 2

    base, path, access, id_token = winners[0]
    print(f"\n=== 2. Using working base: {base} (login {path}) ===\n")

    print("--- GET /api/catalog/documents ---")
    cat = authed_get(base, "/api/catalog/documents", access, id_token)
    print(json.dumps(cat, indent=2))

    print("\n--- GET /api/bl/settings ---")
    settings = authed_get(base, "/api/bl/settings", access, id_token)
    print(json.dumps(settings, indent=2))

    print("\n--- GET /auth/me ---")
    me = authed_get(base, "/auth/me", access, id_token)
    print(json.dumps(me, indent=2))

    document_id = os.getenv("SYBOL_DOCUMENT_ID")
    issuer_key = os.getenv("SYBOL_ISSUER_KEY")

    print("\n=== 3. Issuance format probe (expect 4xx unless IDs are real) ===\n")
    for fmt in probe_issue_formats(base, access, id_token, document_id, issuer_key):
        print(json.dumps(fmt, indent=2))

    print("\n=== 4. Interpretation ===")
    print("  - 201 on catalog_v4 → use catalog_issue_builder + documentId/issuerKey from catalog")
    print("  - 201 on raw_w3c_vc → use vc_builder payload (businessLogic doc style)")
    print("  - 401 → tokens or host wrong")
    print("  - 404 on issue → wrong path or host")
    print("  - 422 → format recognized but validation failed (check catalog claims / IDs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
