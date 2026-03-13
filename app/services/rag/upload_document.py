from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.core.config import Settings, get_settings
from app.models.rag import DocumentUploadResponse, RagNamespace
from app.services.rag.splitters import split_markdown

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings


async def upload_document(
    client: AsyncQdrantClient,
    namespace: RagNamespace,
    filename: str,
    content: str,
    *,
    settings: Settings | None = None,
    embeddings: Embeddings | None = None,
) -> DocumentUploadResponse:
    settings = settings or get_settings()

    if not filename.lower().endswith(".md"):
        raise ValueError("Only .md files are supported")

    chunks = split_markdown(content, settings.rag_chunk_size, settings.rag_chunk_overlap)

    if not chunks:
        raise ValueError("Document is empty or could not be split into chunks")

    chunk_texts = [chunk.page_content for chunk in chunks]

    embeddings = embeddings or GoogleGenerativeAIEmbeddings(
        model=settings.google_embedding_model,
        google_api_key=settings.google_api_key,  # type: ignore[call-arg]
    )
    vectors = await embeddings.aembed_documents(chunk_texts)

    doc_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "namespace": namespace.value,
                "doc_id": doc_id,
                "filename": filename,
                "chunk_index": idx,
                "text": chunk.page_content,
                "headers": chunk.metadata,
                "uploaded_at": now,
            },
        )
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]

    await client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
    )

    return DocumentUploadResponse(
        doc_id=doc_id,
        filename=filename,
        namespace=namespace.value,
        chunk_count=len(chunks),
    )
