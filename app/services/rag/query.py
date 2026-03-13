from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import Settings, get_settings
from app.models.rag import QueryResponse, RagNamespace, SourceChunk
from app.services.rag.prompts import NO_CONTEXT_ANSWER, build_rag_prompt

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings
    from langchain_core.language_models import BaseChatModel


async def query(
    client: AsyncQdrantClient,
    namespace: RagNamespace,
    question: str,
    top_k: int | None = None,
    *,
    settings: Settings | None = None,
    embeddings: Embeddings | None = None,
    llm: BaseChatModel | None = None,
) -> QueryResponse:
    settings = settings or get_settings()
    k = top_k or settings.rag_top_k

    embeddings = embeddings or GoogleGenerativeAIEmbeddings(
        model=settings.google_embedding_model,
        google_api_key=settings.google_api_key,  # type: ignore[call-arg]
    )
    question_vector = await embeddings.aembed_query(question)

    results = await client.query_points(
        collection_name=settings.qdrant_collection,
        query=question_vector,
        query_filter=Filter(
            must=[
                FieldCondition(key="namespace", match=MatchValue(value=namespace.value)),
            ]
        ),
        limit=k,
        with_payload=True,
    )

    sources: list[SourceChunk] = []
    context_parts: list[str] = []
    for point in results.points:
        payload = point.payload or {}
        chunk_text = payload.get("text", "")
        sources.append(
            SourceChunk(
                filename=payload.get("filename", "unknown"),
                chunk_index=payload.get("chunk_index", 0),
                text=chunk_text,
                score=point.score,
            )
        )
        context_parts.append(chunk_text)

    if not context_parts:
        return QueryResponse(answer=NO_CONTEXT_ANSWER, sources=[])

    llm = llm or ChatGoogleGenerativeAI(
        model=settings.google_llm_model,
        google_api_key=settings.google_api_key,
    )
    response = await llm.ainvoke(build_rag_prompt(context_parts, question))

    content = response.content
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block) for block in content
        )

    return QueryResponse(
        answer=content,
        sources=sources,
    )
