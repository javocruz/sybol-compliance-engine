import pytest

from src.api.main import app, lifespan


@pytest.mark.asyncio
async def test_lifespan_stores_index_from_load_index(mocker):
    mock_index = object()
    mock_client = object()
    mocker.patch(
        "src.api.main.load_index",
        return_value=(mock_index, mock_client),
    )

    app.state.index = None
    async with lifespan(app):
        pass

    assert app.state.index is mock_index


@pytest.mark.asyncio
async def test_lifespan_keeps_app_alive_when_index_load_fails(mocker):
    mocker.patch(
        "src.api.main.load_index",
        side_effect=RuntimeError("qdrant is down"),
    )

    app.state.index = "sentinel"
    async with lifespan(app):
        pass

    assert app.state.index is None


def test_app_registers_expected_routes():
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/api/query" in paths
    assert "/api/analyze" in paths
    assert "/api/issue" in paths
    assert "/api/audit/{point_id}" in paths
    assert "/api/status" in paths
    assert "/api/verify/{vc_id}" in paths
    assert "/api/revoke/{vc_id}" in paths


def test_cors_middleware_registered():
    middleware_classes = [mw.cls for mw in app.user_middleware]
    from fastapi.middleware.cors import CORSMiddleware

    assert CORSMiddleware in middleware_classes


@pytest.mark.skipif(
    not (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "frontend"
        / "dist"
        / "index.html"
    ).is_file(),
    reason="frontend/dist not built",
)
def test_spa_fallback_serves_index_when_dist_exists():
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
