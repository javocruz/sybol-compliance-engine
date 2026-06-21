from unittest.mock import MagicMock

from llama_index.core.schema import Document

from rag.ingest import REGULATION_NAME_MAP, chunk_documents, load_documents


def test_regulation_name_map_contains_expected_keys():
    assert REGULATION_NAME_MAP["eu_ai_act"] == "EU AI Act"
    assert REGULATION_NAME_MAP["gdpr"] == "GDPR"
    assert REGULATION_NAME_MAP["codigo_penal"] == "Código Penal (LO 10/1995)"


def test_chunk_documents_extracts_article_and_section():
    docs = [
        Document(
            text="Article 12 covers transparency. Chapter 3 defines obligations.",
            metadata={"regulation_name": "EU AI Act", "regulation_type": "eu_ai_act"},
        )
    ]
    nodes = chunk_documents(docs)
    assert len(nodes) >= 1
    assert nodes[0].metadata["article_number"] == "12"
    assert nodes[0].metadata["section"] == "3"


def test_chunk_documents_unknown_article_and_section():
    docs = [
        Document(
            text="General preamble without structured references.",
            metadata={"regulation_name": "GDPR", "regulation_type": "gdpr"},
        )
    ]
    nodes = chunk_documents(docs)
    assert nodes[0].metadata["article_number"] == "unknown"
    assert nodes[0].metadata["section"] == "unknown"


def test_load_documents(mocker):
    mock_reader = MagicMock()
    mock_reader.load_data.return_value = [
        Document(text="Sample regulation text.", metadata={"regulation_name": "GDPR"})
    ]
    mocker.patch("rag.ingest.SimpleDirectoryReader", return_value=mock_reader)

    docs = load_documents()
    assert len(docs) == 1
    assert docs[0].text == "Sample regulation text."
    mock_reader.load_data.assert_called_once()
