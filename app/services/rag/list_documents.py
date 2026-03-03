from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import Settings, get_settings
from app.models.rag import DocumentInfo, RagNamespace


async def list_documents(
    client: AsyncQdrantClient,
    namespace: RagNamespace,
    *,
    settings: Settings | None = None,
) -> list[DocumentInfo]:
    settings = settings or get_settings()

    points, _ = await client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="namespace", match=MatchValue(value=namespace.value)),
            ]
        ),
        limit=10_000,
        with_payload=True,
        with_vectors=False,
    )

    docs: dict[str, dict] = {}
    for point in points:
        payload = point.payload or {}
        doc_id = payload.get("doc_id", "")
        if doc_id not in docs:
            docs[doc_id] = {
                "doc_id": doc_id,
                "filename": payload.get("filename", "unknown"),
                "namespace": payload.get("namespace", namespace.value),
                "uploaded_at": payload.get("uploaded_at", ""),
                "chunk_count": 0,
            }
        docs[doc_id]["chunk_count"] += 1

    return [DocumentInfo(**doc) for doc in docs.values()]
