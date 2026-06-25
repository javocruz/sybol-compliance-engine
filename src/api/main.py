import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.api.routes.analyze import router as analyze_router
from src.api.routes.audit import router as audit_router
from src.api.routes.auth import router as auth_router
from src.api.routes.issue import router as issue_router
from src.api.routes.query import router as query_router
from src.api.routes.regulations import router as regulations_router
from src.rag.pipeline import load_index

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.api.token_store import create_store

    app.state.index = None
    app.state.token_store = create_store()
    try:
        index, _ = load_index()
        app.state.index = index
    except Exception:
        logger.exception("Failed to build index during startup")
    yield


app = FastAPI(
    title="Sybol Compliance Engine",
    version="0.1.0",
    lifespan=lifespan,
)

_session_secret = os.getenv("SESSION_SECRET_KEY", "dev-only-change-in-production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(SessionMiddleware, secret_key=_session_secret)

app.include_router(analyze_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(issue_router, prefix="/api")
app.include_router(regulations_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}

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
