from fastapi import APIRouter, Depends
from llama_index.core import VectorStoreIndex

from src.api.dependencies import get_index
from src.api.schemas import QueryRequest, QueryResponse
from src.rag.llm import LlmProvider, get_model_name, resolve_provider
from src.rag.query import query_regulations

router = APIRouter(tags=["rag"])


@router.post("/query", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    index: VectorStoreIndex = Depends(get_index),
) -> QueryResponse:
    provider: LlmProvider = resolve_provider(payload.llm_provider)
    result = query_regulations(payload.question, index, llm_provider=provider)
    return QueryResponse(
        answer=result.summary,
        regulation_refs=[
            {"regulation": r.regulation, "article": r.article, "url": r.source_url}
            for r in result.regulation_refs
        ],
        llm_provider=provider,
        llm_model=get_model_name(provider),
    )
