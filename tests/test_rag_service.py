import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.rag import RagNamespace
from app.services.rag.delete_document import delete_document
from app.services.rag.list_documents import list_documents
from app.services.rag.query import query
from app.services.rag.upload_document import upload_document

NAMESPACE = RagNamespace.MEANING_MAP_DOCS
VECTOR_DIM = 3072


@pytest.fixture()
def qdrant():
    client = AsyncMock()
    client.upsert = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture(autouse=True)
def _settings():
    settings = MagicMock()
    settings.qdrant_collection = "meaning_map_test"
    settings.google_api_key = "fake-key"
    settings.google_embedding_model = "gemini-embedding-001"
    settings.google_llm_model = "gemini-3.1-pro-preview"
    settings.rag_chunk_size = 200
    settings.rag_chunk_overlap = 50
    settings.rag_top_k = 3
    with (
        patch("app.services.rag.upload_document.get_settings", return_value=settings),
        patch("app.services.rag.query.get_settings", return_value=settings),
        patch("app.services.rag.delete_document.get_settings", return_value=settings),
        patch("app.services.rag.list_documents.get_settings", return_value=settings),
    ):
        yield settings


@pytest.fixture()
def mock_embeddings():
    with patch("app.services.rag.upload_document.GoogleGenerativeAIEmbeddings") as cls:
        cls.return_value.aembed_documents = AsyncMock(
            side_effect=lambda texts: [[0.1] * VECTOR_DIM for _ in texts]
        )
        yield cls


@pytest.fixture()
def mock_query_embeddings():
    with patch("app.services.rag.query.GoogleGenerativeAIEmbeddings") as cls:
        cls.return_value.aembed_query = AsyncMock(return_value=[0.5] * VECTOR_DIM)
        yield cls


@pytest.fixture()
def mock_llm():
    with patch("app.services.rag.query.ChatGoogleGenerativeAI") as cls:
        response = MagicMock()
        response.content = "The project uses FastAPI as its web framework."
        cls.return_value.ainvoke = AsyncMock(return_value=response)
        yield cls


@pytest.mark.asyncio
async def test_upload_splits_embeds_and_upserts(qdrant, mock_embeddings) -> None:
    content = "# Title\n\n" + ("Lorem ipsum dolor sit amet. " * 30)
    result = await upload_document(qdrant, NAMESPACE, "guide.md", content)

    assert result.filename == "guide.md"
    assert result.namespace == "meaning-map-docs"
    assert result.chunk_count > 0
    assert result.doc_id

    qdrant.upsert.assert_called_once()
    points = qdrant.upsert.call_args.kwargs["points"]
    assert len(points) == result.chunk_count

    payload = points[0].payload
    assert payload["namespace"] == "meaning-map-docs"
    assert payload["filename"] == "guide.md"
    assert "doc_id" in payload
    assert "chunk_index" in payload
    assert "text" in payload
    assert "headers" in payload
    assert "uploaded_at" in payload


@pytest.mark.asyncio
async def test_upload_rejects_non_md(qdrant) -> None:
    with pytest.raises(ValueError, match=r"Only \.md files"):
        await upload_document(qdrant, NAMESPACE, "readme.txt", "content")


@pytest.mark.asyncio
async def test_upload_rejects_empty_content(qdrant, mock_embeddings) -> None:
    with pytest.raises(ValueError, match="empty"):
        await upload_document(qdrant, NAMESPACE, "empty.md", "")


@pytest.mark.asyncio
async def test_query_returns_answer_and_sources(qdrant, mock_query_embeddings, mock_llm) -> None:
    point = MagicMock()
    point.payload = {
        "namespace": "meaning-map-docs",
        "filename": "guide.md",
        "chunk_index": 0,
        "text": "The stack uses FastAPI.",
    }
    point.score = 0.95

    result_obj = MagicMock()
    result_obj.points = [point]
    qdrant.query_points = AsyncMock(return_value=result_obj)

    result = await query(qdrant, NAMESPACE, "What stack?", top_k=3)

    assert result.answer == "The project uses FastAPI as its web framework."
    assert len(result.sources) == 1
    assert result.sources[0].filename == "guide.md"
    assert result.sources[0].score == 0.95

    qdrant.query_points.assert_called_once()
    call_kw = qdrant.query_points.call_args.kwargs
    assert call_kw["query_filter"] is not None


@pytest.mark.asyncio
async def test_query_empty_collection_returns_fallback(qdrant, mock_query_embeddings) -> None:
    result_obj = MagicMock()
    result_obj.points = []
    qdrant.query_points = AsyncMock(return_value=result_obj)

    result = await query(qdrant, NAMESPACE, "Any question?")

    assert "don't have enough information" in result.answer.lower()
    assert result.sources == []


@pytest.mark.asyncio
async def test_delete_filters_by_namespace_and_doc_id(qdrant) -> None:
    mock_points = [MagicMock() for _ in range(3)]
    qdrant.scroll = AsyncMock(return_value=(mock_points, None))

    doc_id = str(uuid.uuid4())
    deleted = await delete_document(qdrant, NAMESPACE, doc_id)

    assert deleted == 3
    qdrant.delete.assert_called_once()

    selector = qdrant.delete.call_args.kwargs["points_selector"]
    field_names = {c.key for c in selector.must}
    assert "namespace" in field_names
    assert "doc_id" in field_names


@pytest.mark.asyncio
async def test_delete_returns_zero_when_not_found(qdrant) -> None:
    qdrant.scroll = AsyncMock(return_value=([], None))

    deleted = await delete_document(qdrant, NAMESPACE, str(uuid.uuid4()))
    assert deleted == 0


@pytest.mark.asyncio
async def test_list_groups_by_doc_id(qdrant) -> None:
    doc_id_a = str(uuid.uuid4())
    doc_id_b = str(uuid.uuid4())

    points = []
    for doc_id, filename, count in [(doc_id_a, "a.md", 3), (doc_id_b, "b.md", 2)]:
        for i in range(count):
            p = MagicMock()
            p.payload = {
                "doc_id": doc_id,
                "filename": filename,
                "namespace": "meaning-map-docs",
                "uploaded_at": "2026-03-02T00:00:00+00:00",
                "chunk_index": i,
            }
            points.append(p)

    qdrant.scroll = AsyncMock(return_value=(points, None))

    result = await list_documents(qdrant, NAMESPACE)

    assert len(result) == 2
    by_id = {d.doc_id: d for d in result}
    assert by_id[doc_id_a].chunk_count == 3
    assert by_id[doc_id_a].filename == "a.md"
    assert by_id[doc_id_b].chunk_count == 2


@pytest.mark.asyncio
async def test_list_empty_namespace(qdrant) -> None:
    qdrant.scroll = AsyncMock(return_value=([], None))

    result = await list_documents(qdrant, NAMESPACE)
    assert result == []
