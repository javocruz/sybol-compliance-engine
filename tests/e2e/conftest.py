"""Shared fixtures for the end-to-end suite (Saba).

These tests drive the real FastAPI app via TestClient over real routes. The
`/api/analyze` path works today with no external services (Tier A demo path).
The `/api/query` (RAG) and `/api/issue` (signed VC) paths depend on Qdrant being
up and — for a real signed credential — Sybol being reachable. Those legs are
gated by `rag_available` / `sybol_configured` so they activate automatically
once Engineering brings Qdrant up and Sybol provides credentials, with no code
change here.
"""

import json
import os
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "qa" / "test_cases" / "golden"


def _qdrant_up() -> bool:
    """True if a Qdrant instance is reachable at QDRANT_URL (default localhost:6333)."""
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    try:
        import httpx

        # Qdrant exposes a liveness endpoint; any 2xx means it's up.
        resp = httpx.get(url.rstrip("/") + "/healthz", timeout=1.0)
        return resp.status_code < 400
    except Exception:
        return False


def _sybol_configured() -> bool:
    """True if the Sybol signing env (tokens + catalog doc) is present."""
    required = ("SYBOL_ACCESS_TOKEN", "SYBOL_ID_TOKEN", "SYBOL_DOCUMENT_ID")
    return all(os.getenv(k) for k in required)


# Module-level so they can be used in skipif marks.
RAG_AVAILABLE = _qdrant_up()
SYBOL_CONFIGURED = _sybol_configured()

requires_rag = pytest.mark.skipif(
    not RAG_AVAILABLE,
    reason="Qdrant not reachable (QDRANT_URL). RAG/issue E2E legs skipped until Engineering brings it up.",
)
requires_sybol = pytest.mark.skipif(
    not SYBOL_CONFIGURED,
    reason="Sybol env not set (SYBOL_ACCESS_TOKEN / SYBOL_ID_TOKEN / SYBOL_DOCUMENT_ID). Signed-VC E2E skipped until Sybol unblocks.",
)


@pytest.fixture(scope="session")
def client():
    """A TestClient for the real app. Session-scoped so the model loads once."""
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def golden_cases():
    """List of (path, label) from the golden manifest; skips if not present."""
    manifest = GOLDEN_DIR / "manifest.json"
    if not manifest.exists():
        pytest.skip(f"Golden dataset not found at {GOLDEN_DIR}")
    records = json.loads(manifest.read_text())
    return [(GOLDEN_DIR / r["file"], r["label"]) for r in records]


def first_of_label(cases, label):
    for path, lbl in cases:
        if lbl == label:
            return path
    return None


CONTENT_TYPE_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def content_type_for(path: Path) -> str:
    return CONTENT_TYPE_BY_SUFFIX.get(path.suffix.lower(), "application/octet-stream")
