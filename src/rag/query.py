import logging

from llama_index.core import VectorStoreIndex

from src.scoring.constants import HALLUCINATION_GUARD_STRICTNESS
from .llm import LlmProvider, complete_with_retry, get_ollama_model, get_synthesis_llm
from .models import ComplianceResult, RegulationRef
from .source_urls import resolve_source_url

logger = logging.getLogger(__name__)

_KNOWN_ARTICLE_PLACEHOLDERS = frozenset({"unknown", "n/a", "none", ""})


def _validate_refs(
    refs: list[RegulationRef],
    known_articles: set[str] | None = None,
) -> list[RegulationRef]:
    """Drop citations with unattributed regulation and/or article per strictness."""
    strictness = HALLUCINATION_GUARD_STRICTNESS.lower()
    valid = []
    for ref in refs:
        reg_unknown = not ref.regulation or ref.regulation.strip().lower() == "unknown"
        art = (ref.article or "").strip()
        art_unknown = art.lower() in _KNOWN_ARTICLE_PLACEHOLDERS

        if reg_unknown:
            logger.warning(
                "Dropping unattributed citation: regulation=%r article=%r",
                ref.regulation,
                ref.article,
            )
            continue

        if strictness in ("article", "both") and art_unknown:
            logger.warning(
                "Dropping citation with unknown article: regulation=%r article=%r",
                ref.regulation,
                ref.article,
            )
            continue

        if (
            strictness == "both"
            and known_articles
            and art
            and art.lower() not in known_articles
        ):
            logger.warning(
                "Dropping citation with article not in retrieved context: %r",
                ref.article,
            )
            continue

        valid.append(ref)
    return valid


def query_regulations(
    query: str,
    index: VectorStoreIndex,
    regulation_type: str | None = None,
    llm_provider: LlmProvider = "mistral",
) -> ComplianceResult:
    from .llm import resolve_provider

    llm_provider = resolve_provider(llm_provider)
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

    known_articles: set[str] = set()
    refs = []
    for node in nodes:
        meta = node.node.metadata
        article = meta.get("article_number", "Unknown")
        if article and str(article).strip().lower() not in _KNOWN_ARTICLE_PLACEHOLDERS:
            known_articles.add(str(article).strip().lower())
        refs.append(
            RegulationRef(
                regulation=meta.get("regulation_name", "Unknown"),
                article=article,
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
        summary = complete_with_retry(llm, prompt, llm_provider)
    except Exception as exc:
        if llm_provider == "ollama":
            raise RuntimeError(
                "Ollama synthesis failed. Ensure Ollama is running "
                f"(`ollama serve`) and model is pulled (`ollama pull {get_ollama_model()}`)."
            ) from exc
        raise RuntimeError("Mistral API synthesis failed.") from exc

    return ComplianceResult(
        summary=summary,
        regulation_refs=_validate_refs(refs, known_articles),
    )
