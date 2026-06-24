from unittest.mock import MagicMock

from rag.query import _validate_refs, query_regulations
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


def test_query_regulations_retrieval_only_without_mistral_key(env_vars, mocker):
    mocker.patch.dict("os.environ", {"MISTRAL_API_KEY": "your_key_here"}, clear=False)
    index = MagicMock()
    node = MagicMock()
    node.node.metadata = {
        "regulation_name": "GDPR",
        "article_number": "5",
        "source_path": "research/regulations/gdpr.pdf",
    }
    node.node.get_content.return_value = "Lawful processing requires a legal basis."
    index.as_retriever.return_value.retrieve.return_value = [node]

    result = query_regulations(query="GDPR lawful basis", index=index)

    assert "Retrieval-only summary" in result.summary
    assert len(result.regulation_refs) == 1


def test_validate_refs_drops_unknown_regulation_or_article():
    refs = [
        RegulationRef(
            regulation="Unknown",
            article="5",
            sourceUrl="https://example.com",
            excerpt="x",
        ),
        RegulationRef(
            regulation="GDPR",
            article="Unknown",
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
    assert len(valid) == 1
    assert valid[0].regulation == "GDPR"
    assert valid[0].article == "5"
