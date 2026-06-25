"""
Exchange SYBOL_EMAIL + SYBOL_PASSWORD for tokens via POST /auth/login.

Usage (from repo root):
  export SYBOL_EMAIL=...
  export SYBOL_PASSWORD=...
  poetry run python -m scripts.sybol_login

Prints export lines for SYBOL_ACCESS_TOKEN and SYBOL_ID_TOKEN (add to src/.env).
"""

import os
import sys

from src.credentials.sybol_client import SybolClient, SybolSigningError


def main() -> int:
    email = os.getenv("SYBOL_EMAIL")
    password = os.getenv("SYBOL_PASSWORD")
    base_url = os.getenv("SYBOL_API_BASE_URL", "https://api.develop.wallet.sybol.id")

    if not email or not password:
        print("Set SYBOL_EMAIL and SYBOL_PASSWORD in the environment.", file=sys.stderr)
        return 1

    client = SybolClient(
        api_base_url=base_url,
        access_token=None,
        id_token=None,
        email=email,
        password=password,
    )

    try:
        data = client.login()
    except SybolSigningError as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        return 1

    access = data.get("accessToken", "")
    id_token = data.get("idToken", "")
    refresh = data.get("refreshToken", "")

    print("Login OK. Add these to src/.env (tokens expire in ~1 hour):\n")
    print(f"SYBOL_ACCESS_TOKEN={access}")
    print(f"SYBOL_ID_TOKEN={id_token}")
    if refresh:
        print(f"SYBOL_REFRESH_TOKEN={refresh}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
