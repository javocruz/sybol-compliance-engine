"""End-to-end flow through the live FastAPI app (Saba, Step 4 / demo readiness).

Tiers mirror the demo plan:
  Tier A — upload -> /api/analyze -> score + breakdown        (works today)
  Tier B — /api/query returns regulation refs                 (needs Qdrant)
  Tier C — /api/issue returns a signed VC                      (needs Sybol)

Tier A runs unconditionally and is the guaranteed demo path. Tier B/C are gated
by `requires_rag` / `requires_sybol` and turn on automatically once those
services are available — no edits needed here.
"""

import io

import pytest

from tests.e2e.conftest import (
    content_type_for,
    first_of_label,
    requires_rag,
    requires_sybol,
)

# --- liveness ----------------------------------------------------------------


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- Tier A: analyze path (no external services) -----------------------------


def _post_analyze(client, path):
    with path.open("rb") as fh:
        return client.post(
            "/api/analyze",
            files={"file": (path.name, fh.read(), content_type_for(path))},
        )


def test_analyze_authentic_image_end_to_end(client, golden_cases):
    path = first_of_label(golden_cases, "authentic")
    if path is None:
        pytest.skip("no authentic image in golden set")
    resp = _post_analyze(client, path)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Full response contract (AnalyzeResponse). NOTE: ScoreBreakdown uses field
    # aliases (m/a/v/p) and FastAPI serializes by alias, so the wire keys are
    # m/a/v/p — not the python field names. This is the shape Jana's demo /
    # frontend consumes.
    assert 0.0 <= body["authenticity_score"] <= 1.0
    assert set(body["score_breakdown"]) == {"m", "a", "v", "p"}
    assert all(0.0 <= body["score_breakdown"][k] <= 1.0 for k in "mavp")
    assert body["compliance_status"] in {"compliant", "non-compliant", "review"}
    assert len(body["media_hash"]) == 64  # sha256 hex
    assert body["model_version"]
    assert body["analysis_timestamp"]

    # TC-001 through the API: authentic -> compliant, score in band.
    assert body["compliance_status"] == "compliant"
    assert 0.8 <= body["authenticity_score"] <= 1.0


def test_analyze_ai_generated_image_end_to_end(client, golden_cases):
    path = first_of_label(golden_cases, "ai_generated")
    if path is None:
        pytest.skip("no ai_generated image in golden set")
    resp = _post_analyze(client, path)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # TC-002 through the API: AI-generated -> non-compliant, low score.
    assert body["compliance_status"] == "non-compliant"
    assert 0.0 <= body["authenticity_score"] <= 0.3


def test_analyze_is_deterministic_over_http(client, golden_cases):
    # Same upload twice -> identical score + hash (reproducibility, end to end).
    path = first_of_label(golden_cases, "authentic")
    if path is None:
        pytest.skip("no authentic image in golden set")
    first = _post_analyze(client, path).json()
    second = _post_analyze(client, path).json()
    assert first["media_hash"] == second["media_hash"]
    assert first["authenticity_score"] == second["authenticity_score"]
    assert first["compliance_status"] == second["compliance_status"]


def test_analyze_rejects_corrupted_upload(client):
    # End-to-end "no crash" guard: a corrupt upload returns a clean 4xx.
    resp = client.post(
        "/api/analyze",
        files={
            "file": (
                "broken.png",
                io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\xff" * 4),
                "image/png",
            )
        },
    )
    assert resp.status_code == 400, resp.text
    assert "detail" in resp.json()


# --- Tier B: RAG query (needs Qdrant) ----------------------------------------


@requires_rag
def test_query_returns_regulation_refs(client):
    resp = client.post(
        "/api/query", json={"question": "What applies to AI-generated images?"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["answer"], str) and body["answer"]
    assert isinstance(body["regulation_refs"], list)
    # When refs are returned they must carry the wire shape used by the VC.
    for ref in body["regulation_refs"]:
        assert {"regulation", "article", "url"} <= set(ref)


# --- Tier C: full issue -> signed VC (needs Qdrant + Sybol) ------------------


@requires_rag
def test_issue_builds_unsigned_vc(client, golden_cases):
    # With RAG up but Sybol not configured, /api/issue should still build the
    # unsigned VC payload end to end.
    path = first_of_label(golden_cases, "authentic")
    if path is None:
        pytest.skip("no authentic image in golden set")
    with path.open("rb") as fh:
        resp = client.post(
            "/api/issue",
            files={"file": (path.name, fh.read(), content_type_for(path))},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vc_id"]
    assert body.get("vc_payload") is not None


@requires_rag
@requires_sybol
def test_issue_returns_signed_vc(client, golden_cases):
    # Full Tier C: a real signed credential from Sybol.
    path = first_of_label(golden_cases, "authentic")
    if path is None:
        pytest.skip("no authentic image in golden set")
    with path.open("rb") as fh:
        resp = client.post(
            "/api/issue",
            files={"file": (path.name, fh.read(), content_type_for(path))},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["signed"] is True
    assert body.get("signed_vc") is not None
    assert "proof" in body["signed_vc"]
