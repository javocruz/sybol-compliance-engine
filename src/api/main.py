import logging
import os
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.logging_config import RequestLoggingMiddleware, configure_logging
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routes.analyze import router as analyze_router
from src.api.routes.audit import router as audit_router
from src.api.routes.issue import router as issue_router
from src.api.routes.query import router as query_router
from src.api.routes.regulations import router as regulations_router
from src.api.routes.revoke import router as revoke_router
from src.api.routes.status import router as status_router
from src.api.routes.verify import router as verify_router
from src.rag.pipeline import load_index

logger = logging.getLogger(__name__)

VC_VERSION = "1.1"


def _git_commit() -> str:
    env = os.getenv("GIT_COMMIT")
    if env:
        return env
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                cwd=Path(__file__).resolve().parents[2],
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _cors_origins() -> list[str]:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    public = (os.getenv("PUBLIC_BASE_URL") or "").rstrip("/")
    if public:
        origins.append(public)
        if public.startswith("https://"):
            http_variant = "http://" + public.removeprefix("https://")
            origins.append(http_variant)
    app_env = os.getenv("APP_ENV", "dev")
    if app_env != "production":
        origins.append("*")
    return origins


def _warmup_models() -> None:
    if os.getenv("WARMUP_ON_START", "false").lower() not in ("1", "true", "yes"):
        return
    try:
        from src.scoring.pipeline import load_scoring_pipeline
        from src.scoring.detector import get_deepfake_model

        load_scoring_pipeline()
        get_deepfake_model()
        logger.info("Model warm-up complete")
    except Exception:
        logger.exception("Model warm-up failed (non-fatal)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.started_at = time.time()
    app.state.git_commit = _git_commit()
    app.state.vc_version = VC_VERSION
    app.state.index = None
    try:
        index, _ = load_index()
        app.state.index = index
    except Exception:
        logger.exception("Failed to build index during startup")
    _warmup_models()
    yield


app = FastAPI(
    title="Sybol Compliance Engine",
    version="0.1.0",
    description=(
        "Media authenticity scoring, EU regulation RAG, and Sybol-signed W3C VCs. "
        "Issued credentials include an `evidenceUrl` pointing to `/api/audit/{point_id}`."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {"name": "scoring", "description": "Authenticity analysis"},
        {"name": "rag", "description": "Regulation Q&A"},
        {"name": "credentials", "description": "VC issuance and verification"},
        {"name": "status", "description": "Health and readiness"},
    ],
)

_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if "*" not in _origins else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/health", tags=["status"])
async def health():
    return {"status": "ok"}


app.include_router(analyze_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(issue_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(status_router, prefix="/api")
app.include_router(verify_router, prefix="/api")
app.include_router(revoke_router, prefix="/api")
app.include_router(regulations_router, prefix="/api")

_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404)
        file = _dist / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_dist / "index.html")
