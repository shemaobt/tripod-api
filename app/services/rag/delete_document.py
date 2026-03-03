from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import get_settings
from app.models.rag import RagNamespace


async def delete_document(
    client: AsyncQdrantClient,
    namespace: RagNamespace,
    doc_id: str,
) -> int:
    """Delete all Qdrant points belonging to a document in a namespace.

    Returns the number of deleted points (best-effort count via pre-scroll).
    """
    settings = get_settings()

    existing = await client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="namespace", match=MatchValue(value=namespace.value)),
                FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
            ]
        ),
        limit=10_000,
        with_payload=False,
        with_vectors=False,
    )
    deleted_count = len(existing[0])

    await client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[
                FieldCondition(key="namespace", match=MatchValue(value=namespace.value)),
                FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
            ]
        ),
    )

    return deleted_count
