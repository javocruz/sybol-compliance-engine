import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.api.main import app
from src.scoring.models import ComplianceStatus, ScoringResult, SignalBreakdown


@pytest.fixture
def png_bytes():
    image = Image.new("RGB", (32, 32), color=(10, 20, 30))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_analyze_returns_score_breakdown_object(png_bytes):
    mock_result = ScoringResult(
        authenticity_score=0.42,
        score_breakdown=SignalBreakdown(m=0.1, a=0.2, v=0.3, p=0.4),
        compliance_status=ComplianceStatus.REVIEW,
        media_hash="abc",
        model_version="test-model",
    )
    with patch("src.api.routes.analyze.score_image", return_value=mock_result):
        client = TestClient(app)
        response = client.post(
            "/api/analyze",
            files={"file": ("test.png", png_bytes, "image/png")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["score_breakdown"] == {
        "m": 0.1,
        "a": 0.2,
        "v": 0.3,
        "p": 0.4,
    }
