from fastapi import APIRouter, Request

from src.api.dependencies import Settings, get_settings, get_sybol_client

router = APIRouter(tags=["status"])


@router.get("/status", summary="Ceremony stack health and readiness")
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

    return {
        "api": "ok",
        "qdrant": qdrant_status,
        "rag_index_loaded": rag_index_loaded,
        "regulations_chunks": regulations_chunks,
        "sybol_configured": sybol.is_configured,
        "model_loaded": model_loaded,
        "public_base_url": settings.public_base_url,
    }
