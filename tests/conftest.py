import io
from unittest.mock import MagicMock

import pytest
from PIL import Image


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "test-key")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-mistral-key")


@pytest.fixture
def mock_qdrant_client(mocker):
    client = MagicMock()
    client.get_collections.return_value.collections = []
    mocker.patch("rag.indexer.QdrantClient", return_value=client)
    mocker.patch("rag.indexer.QdrantVectorStore")
    return client


@pytest.fixture
def mock_embed_model(mocker):
    model = MagicMock()
    mocker.patch("rag.embeder.HuggingFaceEmbedding", return_value=model)
    mocker.patch("rag.pipeline.get_embedding_model", return_value=model)
    return model


@pytest.fixture
def mock_synthesis_llm(mocker):
    llm = MagicMock()
    llm.complete.return_value = "Synthesized compliance summary."
    mocker.patch("rag.llm.get_synthesis_llm", return_value=llm)
    mocker.patch("rag.query.get_synthesis_llm", return_value=llm)
    return llm


@pytest.fixture
def mock_mistral(mock_synthesis_llm):
    """Backward-compatible alias for tests that patch Mistral via synthesis LLM."""
    return mock_synthesis_llm


@pytest.fixture
def mock_vector_index(mocker):
    index = MagicMock()
    node = MagicMock()
    node.node.metadata = {
        "regulation_name": "GDPR",
        "article_number": "5",
        "source_path": "/research/regulations/gdpr.pdf",
    }
    node.node.get_content.return_value = "Article 5 requires lawful processing."
    index.as_retriever.return_value.retrieve.return_value = [node]
    return index


@pytest.fixture
def sample_document_nodes():
    from llama_index.core.schema import Document, TextNode

    doc = Document(
        text="Article 5 of GDPR requires lawful processing. Section 2 covers consent.",
        metadata={"regulation_name": "GDPR", "regulation_type": "gdpr"},
    )
    splitter_nodes = [
        TextNode(
            text=doc.text,
            metadata=dict(doc.metadata),
        )
    ]
    return splitter_nodes


@pytest.fixture
def sample_png_bytes():
    image = Image.new("RGB", (64, 64), color=(120, 80, 200))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_jpeg_bytes():
    image = Image.new("RGB", (128, 128), color=(40, 120, 60))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def corrupt_bytes():
    return b"not-an-image-at-all"


@pytest.fixture
def mock_deepfake_model(mocker):
    bundle = MagicMock()
    bundle.version = "dima806/deepfake_vs_real_image_detection@test"
    mocker.patch("scoring.detector.get_deepfake_model", return_value=bundle)
    mocker.patch("scoring.detector.predict_authenticity_score", return_value=0.85)
    mocker.patch("scoring.scorer.get_deepfake_model", return_value=bundle)
    return bundle


@pytest.fixture
def authentic_reference_dir(tmp_path):
    directory = tmp_path / "authentic"
    directory.mkdir()
    for idx, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        image = Image.new("RGB", (32, 32), color=color)
        image.save(directory / f"authentic_{idx}.png")
    return directory
