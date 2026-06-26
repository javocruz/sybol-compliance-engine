import os

from fastapi import APIRouter, Depends, HTTPException
from llama_index.core import VectorStoreIndex

from src.api.dependencies import get_index
from src.api.schemas import QueryRequest, QueryResponse
from src.rag.llm import (
    LlmProvider,
    check_ollama_available,
    get_model_name,
    resolve_provider,
)
from src.rag.query import query_regulations

router = APIRouter(tags=["rag"])


@router.post("/query", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    index: VectorStoreIndex = Depends(get_index),
) -> QueryResponse:
    requested: LlmProvider = payload.llm_provider
    if requested == "mistral" and not os.environ.get("MISTRAL_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail=(
                "MISTRAL_API_KEY is not configured on this server. "
                "Use local Ollama for dev, or set MISTRAL_API_KEY in src/.env."
            ),
        )

    provider: LlmProvider = resolve_provider(requested)

    if provider == "ollama":
        ok, detail = check_ollama_available()
        if not ok:
            raise HTTPException(
                status_code=503,
                detail=detail or "Ollama is not available on this server.",
            )

    try:
        result = query_regulations(payload.question, index, llm_provider=provider)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"RAG query failed: {exc}",
        ) from exc

    return QueryResponse(
        answer=result.summary,
        regulation_refs=[
            {"regulation": r.regulation, "article": r.article, "url": r.source_url}
            for r in result.regulation_refs
        ],
        llm_provider=provider,
        llm_model=get_model_name(provider),
    )
