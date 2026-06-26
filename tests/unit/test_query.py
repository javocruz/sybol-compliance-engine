from unittest.mock import MagicMock

from rag.query import _dedupe_refs, _validate_refs, query_regulations
from src.rag.models import RegulationRef


def test_query_regulations_returns_compliance_result(
    mock_mistral, mock_vector_index, env_vars
):
    result = query_regulations(
        query="What are GDPR data processing requirements?",
        index=mock_vector_index,
    )

    assert result.summary == "Synthesized compliance summary."
    assert len(result.regulation_refs) == 1
    assert result.regulation_refs[0].regulation == "GDPR"
    assert result.regulation_refs[0].article == "5"
    mock_mistral.complete.assert_called_once()


def test_query_regulations_with_ollama_provider(
    mock_synthesis_llm, mock_vector_index, env_vars, mocker
):
    mock_get_llm = mocker.patch("rag.query.get_synthesis_llm", return_value=mock_synthesis_llm)

    result = query_regulations(
        query="AI transparency rules",
        index=mock_vector_index,
        llm_provider="ollama",
    )

    assert result.summary == "Synthesized compliance summary."
    mock_get_llm.assert_called_once_with("ollama")


def test_query_regulations_with_regulation_type_filter(
    mock_mistral, mock_vector_index, env_vars
):
    result = query_regulations(
        query="AI transparency rules",
        index=mock_vector_index,
        regulation_type="eu_ai_act",
    )

    assert result.summary == "Synthesized compliance summary."
    mock_vector_index.as_retriever.assert_called_once()
    call_kwargs = mock_vector_index.as_retriever.call_args.kwargs
    assert call_kwargs["similarity_top_k"] == 5
    assert call_kwargs["filters"] is not None


def test_query_regulations_drops_unknown_metadata(mock_mistral, env_vars, mocker):
    index = MagicMock()
    node = MagicMock()
    node.node.metadata = {}
    node.node.get_content.return_value = "Short excerpt."
    index.as_retriever.return_value.retrieve.return_value = [node]

    result = query_regulations(query="test query", index=index)

    assert result.regulation_refs == []


def test_dedupe_refs_collapses_identical_citations():
    refs = [
        RegulationRef(
            regulation="EU AI Act",
            article="unknown",
            sourceUrl="/api/regulations/eu_ai_act.pdf",
            excerpt="a",
        ),
        RegulationRef(
            regulation="EU AI Act",
            article="unknown",
            sourceUrl="/api/regulations/eu_ai_act.pdf",
            excerpt="b",
        ),
        RegulationRef(
            regulation="GDPR",
            article="5",
            sourceUrl="/api/regulations/gdpr.pdf",
            excerpt="c",
        ),
    ]
    assert len(_dedupe_refs(refs)) == 2


def test_validate_refs_drops_only_unattributed_regulation():
    # Only a missing/unknown *regulation* drops a citation; a known regulation
    # with an unknown article is still useful (the source PDF is linked).
    refs = [
        RegulationRef(
            regulation="Unknown",
            article="5",
            sourceUrl="https://example.com",
            excerpt="x",
        ),
        RegulationRef(
            regulation="GDPR",
            article="unknown",
            sourceUrl="https://example.com",
            excerpt="y",
        ),
        RegulationRef(
            regulation="GDPR",
            article="5",
            sourceUrl="https://example.com",
            excerpt="z",
        ),
    ]
    valid = _validate_refs(refs)
    assert len(valid) == 2
    assert all(ref.regulation == "GDPR" for ref in valid)
