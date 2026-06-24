from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.rag.ingest import REGULATIONS_DIR

router = APIRouter(tags=["regulations"])

_ALLOWED_PDFS = {path.name for path in REGULATIONS_DIR.glob("*.pdf")}


@router.get(
    "/regulations/{filename}",
    summary="Download an ingested regulation PDF",
    responses={404: {"description": "Unknown or missing regulation file"}},
)
async def serve_regulation_pdf(filename: str):
    if filename not in _ALLOWED_PDFS:
        raise HTTPException(404, "Regulation document not found")

    path = REGULATIONS_DIR / filename
    if not path.is_file():
        raise HTTPException(404, "Regulation document not found")

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
    )
