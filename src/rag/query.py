import logging
import os

from llama_index.core import VectorStoreIndex
from llama_index.llms.mistralai import MistralAI

from .models import ComplianceResult, RegulationRef

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """
You are a EU regulatory compliance expert. Using ONLY the provided regulation excerpts,
answer the query. Be precise about which article you are citing.
If a requirement is not covered by the excerpts, say so explicitly.
"""


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


def _mistral_api_key() -> str | None:
    key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not key or key in {"your_key_here", "TBD"}:
        return None
    return key


def _retrieval_only_summary(query: str, nodes) -> str:
    if not nodes:
        return f"No regulation excerpts retrieved for: {query}"
    intro = (
        "Retrieval-only summary (set MISTRAL_API_KEY for LLM synthesis). "
        "Top excerpts:"
    )
    snippets = [n.node.get_content()[:240].replace("\n", " ") for n in nodes[:3]]
    return intro + " " + " | ".join(snippets)


def query_regulations(
    query: str,
    index: VectorStoreIndex,
    regulation_type: str | None = None,
) -> ComplianceResult:
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
                source_url=meta.get("source_path", ""),
                excerpt=node.node.get_content()[:300],
            )
        )

    api_key = _mistral_api_key()
    if api_key:
        llm = MistralAI(
            model="mistral-large-latest",
            api_key=api_key,
            system_prompt=SYNTHESIS_PROMPT,
        )
        context = "\n\n---\n\n".join(n.node.get_content() for n in nodes)
        response = llm.complete(f"Context:\n{context}\n\nQuery: {query}")
        summary = str(response)
    else:
        logger.warning("MISTRAL_API_KEY not set — using retrieval-only RAG summary.")
        summary = _retrieval_only_summary(query, nodes)

    return ComplianceResult(
        summary=summary,
        regulation_refs=_validate_refs(refs),
    )
