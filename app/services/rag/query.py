from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import get_settings
from app.models.rag import QueryResponse, RagNamespace, SourceChunk
from app.services.rag.prompts import NO_CONTEXT_ANSWER, build_rag_prompt


async def query(
    client: AsyncQdrantClient,
    namespace: RagNamespace,
    question: str,
    top_k: int | None = None,
) -> QueryResponse:
    """Search for relevant chunks in a namespace and generate an answer with Gemini."""
    settings = get_settings()
    k = top_k or settings.rag_top_k

    embeddings_model = GoogleGenerativeAIEmbeddings(
        model=settings.google_embedding_model,
        google_api_key=settings.google_api_key,
    )
    question_vector = await embeddings_model.aembed_query(question)

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

    llm = ChatGoogleGenerativeAI(
        model=settings.google_llm_model,
        google_api_key=settings.google_api_key,
    )
    response = await llm.ainvoke(build_rag_prompt(context_parts, question))

    content = response.content
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )

    return QueryResponse(
        answer=content,
        sources=sources,
    )
