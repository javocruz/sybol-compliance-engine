import os
import time

from fastapi import APIRouter, Request

from src.api.dependencies import Settings, get_settings, get_sybol_client
from src.scoring.constants import PLATT_ENABLED

router = APIRouter(tags=["status"])


@router.get("/status", summary="Stack health and readiness")
async def system_status(request: Request) -> dict:
    settings: Settings = get_settings()
    sybol = get_sybol_client(settings)

    qdrant_status = "unavailable"
    regulations_chunks: int | None = None
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            url=settings.qdrant_url, api_key=settings.qdrant_api_key
        )
        client.get_collections()
        qdrant_status = "ok"
        try:
            info = client.get_collection(settings.qdrant_collection)
            regulations_chunks = info.points_count
        except Exception:
            regulations_chunks = None
    except Exception:
        qdrant_status = "unavailable"

    model_loaded = False
    try:
        from src.scoring.detector import get_deepfake_model

        get_deepfake_model()
        model_loaded = True
    except Exception:
        model_loaded = False

    rag_index_loaded = getattr(request.app.state, "index", None) is not None
    started_at = getattr(request.app.state, "started_at", None)
    uptime_seconds = round(time.time() - started_at, 1) if started_at else None

    from src.rag.llm import check_ollama_available, get_ollama_base_url, get_ollama_model

    ollama_ok, ollama_detail = check_ollama_available()

    return {
        "api": "ok",
        "qdrant": qdrant_status,
        "rag_index_loaded": rag_index_loaded,
        "regulations_chunks": regulations_chunks,
        "sybol_configured": sybol.is_configured,
        "model_loaded": model_loaded,
        "public_base_url": settings.public_base_url,
        "git_commit": getattr(request.app.state, "git_commit", None),
        "uptime_seconds": uptime_seconds,
        "platt_enabled": PLATT_ENABLED,
        "vc_version": getattr(request.app.state, "vc_version", "1.1"),
        "app_env": settings.app_env,
        "ollama_available": ollama_ok,
        "ollama_model": get_ollama_model(),
        "ollama_base_url": get_ollama_base_url(),
        "ollama_detail": ollama_detail,
        "mistral_configured": bool(os.environ.get("MISTRAL_API_KEY")),
    }
