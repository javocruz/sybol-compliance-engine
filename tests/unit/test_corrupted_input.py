"""TC-004 — corrupted / malformed input is rejected cleanly, no crash (Saba).

README_Saba TC-004: "corrupted file -> clean error, no crash".

test_preprocess.py already covers the raw preprocess() layer for a couple of
cases. This file completes TC-004 across the two layers that matter for the demo:

  1. score_image() — the full pipeline must surface ScoringError (with a useful
     `code`) for every corruption mode, and must do so *before* the deepfake
     model runs, so these tests need no model/torch.
  2. POST /api/analyze and /api/issue — must return HTTP 400 (not 500 / not a
     stack trace) for the same bad inputs. This is the actual "no crash"
     guarantee a demo upload relies on.

Corruption modes exercised:
  * empty / zero-byte upload
  * random garbage (no recognizable header)
  * valid magic header but truncated/garbage body (the realistic "broken upload")
  * a real image mislabeled with an unsupported content-type
"""

import io

import pytest
from PIL import Image

from scoring.preprocess import ScoringError, preprocess

# ---- corrupt payload builders ------------------------------------------------


def _truncated_png() -> bytes:
    # Valid PNG signature so _detect_format accepts it, then garbage -> load() fails.
    return b"\x89PNG\r\n\x1a\n" + b"\x00\xff" * 16


def _truncated_jpeg() -> bytes:
    # Valid JPEG SOI marker, then a truncated body.
    return b"\xff\xd8\xff\xe0" + b"\x00" * 8


def _valid_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


# (label, payload, expected ScoringError.code) for the pipeline-level checks.
CORRUPTION_CASES = [
    ("empty", b"", "empty_file"),
    ("garbage", b"this is definitely not an image", "unsupported_format"),
    ("truncated_png", _truncated_png(), "corrupted_file"),
    ("truncated_jpeg", _truncated_jpeg(), "corrupted_file"),
]


# ---- pipeline layer ----------------------------------------------------------


@pytest.mark.parametrize(
    "payload, code",
    [(p, c) for _, p, c in CORRUPTION_CASES],
    ids=[n for n, _, _ in CORRUPTION_CASES],
)
def test_preprocess_raises_scoring_error_with_code(payload, code):
    with pytest.raises(ScoringError) as exc:
        preprocess(payload)
    assert exc.value.code == code


@pytest.mark.parametrize(
    "payload",
    [p for _, p, _ in CORRUPTION_CASES],
    ids=[n for n, _, _ in CORRUPTION_CASES],
)
def test_score_image_surfaces_scoring_error(payload):
    # The full pipeline must raise ScoringError (not a raw PIL/IO error) and must
    # fail in preprocessing before the deepfake model loads.
    from scoring.pipeline import score_image

    with pytest.raises(ScoringError):
        score_image(payload, filename="upload.bin")


def test_unsupported_content_type_rejected_even_for_real_image():
    # A genuine PNG mislabeled as a TIFF must still be rejected (content-type guard).
    with pytest.raises(ScoringError) as exc:
        preprocess(_valid_png_bytes(), content_type="image/tiff")
    assert exc.value.code == "unsupported_format"


def test_scoring_error_carries_message_and_code():
    # The error must be inspectable (message + machine-readable code) for the API.
    with pytest.raises(ScoringError) as exc:
        preprocess(b"")
    assert str(exc.value)  # non-empty human message
    assert exc.value.code == "empty_file"


# ---- endpoint layer: must return 400, never crash ---------------------------


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from api.main import app

    return TestClient(app)


@pytest.mark.parametrize(
    "payload, ctype",
    [
        (b"", "image/png"),
        (b"not an image", "image/png"),
        (_truncated_png(), "image/png"),
        (_truncated_jpeg(), "image/jpeg"),
        (_valid_png_bytes(), "application/pdf"),  # unsupported content-type
    ],
)
def test_analyze_returns_400_not_500(client, payload, ctype):
    resp = client.post(
        "/api/analyze",
        files={"file": ("upload", io.BytesIO(payload), ctype)},
    )
    # The contract is "clean error": a 4xx, never a 500 / unhandled exception.
    assert resp.status_code == 400, resp.text
    assert "detail" in resp.json()


def test_analyze_rejects_missing_file(client):
    # No file part at all -> FastAPI validation 422, still a clean error (no crash).
    resp = client.post("/api/analyze")
    assert resp.status_code == 422


def test_issue_rejects_corrupted_upload_cleanly(client):
    # The issue endpoint runs the same scoring preprocessing. A corrupt upload
    # must produce a clean 4xx, never a 500. Note: the route checks RAG
    # availability first, so with Qdrant down this surfaces as 503 (RAG
    # unavailable) before the 400 corrupt-file path; both are clean errors and
    # neither is a crash. When RAG is up, this becomes a 400.
    resp = client.post(
        "/api/issue",
        files={"file": ("upload", io.BytesIO(_truncated_png()), "image/png")},
    )
    assert resp.status_code in (400, 503), resp.text
    assert resp.status_code != 500
    assert "detail" in resp.json()
