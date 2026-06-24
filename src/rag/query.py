import logging

from llama_index.core import VectorStoreIndex

from .llm import LlmProvider, get_ollama_model, get_synthesis_llm
from .models import ComplianceResult, RegulationRef
from .source_urls import resolve_source_url

logger = logging.getLogger(__name__)


def _validate_refs(refs: list[RegulationRef]) -> list[RegulationRef]:
    """Drop citations with missing attribution (Unknown regulation/article)."""
    valid = []
    for ref in refs:
        if ref.regulation == "Unknown" or ref.article == "Unknown":
            logger.warning(
                "Dropping hallucinated/unattributed citation: regulation=%r article=%r",
                ref.regulation,
                ref.article,
            )
        else:
            valid.append(ref)
    return valid


def query_regulations(
    query: str,
    index: VectorStoreIndex,
    regulation_type: str | None = None,
    llm_provider: LlmProvider = "mistral",
) -> ComplianceResult:
    llm = get_synthesis_llm(llm_provider)

    filters = None
    if regulation_type:
        from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="regulation_type",
                    value=regulation_type,
                )
            ]
        )

    retriever = index.as_retriever(similarity_top_k=5, filters=filters)
    nodes = retriever.retrieve(query)

    refs = []
    for node in nodes:
        meta = node.node.metadata
        refs.append(
            RegulationRef(
                regulation=meta.get("regulation_name", "Unknown"),
                article=meta.get("article_number", "Unknown"),
                source_url=resolve_source_url(
                    meta.get("source_path", ""),
                    meta.get("regulation_type"),
                ),
                excerpt=node.node.get_content()[:300],
            )
        )

    context = "\n\n---\n\n".join(n.node.get_content() for n in nodes)
    prompt = f"Context:\n{context}\n\nQuery: {query}"

    try:
        response = llm.complete(prompt)
    except Exception as exc:
        if llm_provider == "ollama":
            raise RuntimeError(
                "Ollama synthesis failed. Ensure Ollama is running "
                f"(`ollama serve`) and model is pulled (`ollama pull {get_ollama_model()}`)."
            ) from exc
        raise RuntimeError("Mistral API synthesis failed.") from exc

    summary = str(response)

    return ComplianceResult(
        summary=summary,
        regulation_refs=_validate_refs(refs),
    )
