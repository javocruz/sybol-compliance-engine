from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from src.api.dependencies import get_settings

# Collection name constant used across the RAG indexer (default)
COLLECTION_NAME = "regulations"


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(settings.qdrant_url, api_key=settings.qdrant_api_key)


def _delete_collection_if_exists(client: QdrantClient) -> None:
    collections = client.get_collections().collections
    for coll in collections:
        if getattr(coll, "name", None) == COLLECTION_NAME:
            client.delete_collection(COLLECTION_NAME)
            return


def load_documents() -> list[Document]:
    # Replace with your PDF ingestion once you hook regulation parsing in
    return [
        Document(
            text="Temporary sample regulation text.",
            metadata={"source": "placeholder"},
        )
    ]


def load_index(embed_model) -> tuple[object, QdrantClient]:
    client = get_qdrant_client()
    vector_store = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME)
    index = VectorStoreIndex.from_vector_store(vector_store, embed_model)
    return index, client


def build_index(
    nodes, embed_model, recreate_collection: bool = True
) -> tuple[object, QdrantClient]:
    client = get_qdrant_client()
    if recreate_collection:
        _delete_collection_if_exists(client)

    vector_store = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME)
    # StorageContext.from_defaults is patched in tests; use it to create storage
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
    )
    return index, client
