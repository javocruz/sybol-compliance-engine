from unittest.mock import MagicMock

from rag.indexer import (
    COLLECTION_NAME,
    _delete_collection_if_exists,
    build_index,
    get_qdrant_client,
    load_index,
)


def test_get_qdrant_client(env_vars, mocker):
    mock_cls = mocker.patch("rag.indexer.QdrantClient")
    client = get_qdrant_client()
    mock_cls.assert_called_once_with(
        "http://localhost:6333",
        api_key="test-key",
    )
    assert client is mock_cls.return_value


def test_delete_collection_if_exists_deletes_when_present():
    client = MagicMock()
    collection = MagicMock()
    collection.name = COLLECTION_NAME
    client.get_collections.return_value.collections = [collection]

    _delete_collection_if_exists(client)
    client.delete_collection.assert_called_once_with(COLLECTION_NAME)


def test_delete_collection_if_exists_skips_when_absent():
    client = MagicMock()
    client.get_collections.return_value.collections = []

    _delete_collection_if_exists(client)
    client.delete_collection.assert_not_called()


def test_load_index(mock_qdrant_client, mock_embed_model, mocker):
    mock_index = MagicMock()
    mocker.patch(
        "rag.indexer.VectorStoreIndex.from_vector_store",
        return_value=mock_index,
    )

    index, client = load_index(mock_embed_model)
    assert index is mock_index
    assert client is mock_qdrant_client


def test_build_index_recreates_collection_when_present(
    mock_qdrant_client, mock_embed_model, mocker
):
    collection = MagicMock()
    collection.name = COLLECTION_NAME
    mock_qdrant_client.get_collections.return_value.collections = [collection]

    mock_index = MagicMock()
    mock_vector_store_index = mocker.patch(
        "rag.indexer.VectorStoreIndex", return_value=mock_index
    )
    mocker.patch("rag.indexer.StorageContext.from_defaults")
    nodes = [MagicMock()]

    index, client = build_index(nodes, mock_embed_model, recreate_collection=True)
    assert index is mock_index
    assert client is mock_qdrant_client
    mock_qdrant_client.delete_collection.assert_called_once_with(COLLECTION_NAME)
    mock_vector_store_index.assert_called_once_with(
        nodes,
        storage_context=mocker.ANY,
        embed_model=mock_embed_model,
    )


def test_build_index_skips_recreate_when_disabled(
    mock_qdrant_client, mock_embed_model, mocker
):
    mock_index = MagicMock()
    mocker.patch("rag.indexer.VectorStoreIndex", return_value=mock_index)
    mocker.patch("rag.indexer.StorageContext.from_defaults")
    nodes = [MagicMock()]

    index, client = build_index(nodes, mock_embed_model, recreate_collection=False)
    assert index is mock_index
    mock_qdrant_client.get_collections.assert_not_called()
