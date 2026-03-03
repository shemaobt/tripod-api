import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.rag import RagNamespace

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_qdrant_client():
    """Return an AsyncMock that mimics AsyncQdrantClient."""
    client = AsyncMock()
    client.upsert = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture()
def _patch_settings():
    """Patch get_settings to return test-friendly values (no real keys needed)."""
    mock_settings = MagicMock()
    mock_settings.qdrant_collection = "meaning_map_test"
    mock_settings.google_api_key = "fake-key"
    mock_settings.google_embedding_model = "models/text-embedding-004"
    mock_settings.google_llm_model = "gemini-3.1-pro-preview"
    mock_settings.rag_chunk_size = 200
    mock_settings.rag_chunk_overlap = 50
    mock_settings.rag_top_k = 3
    with (
        patch("app.services.rag.upload_document.get_settings", return_value=mock_settings),
        patch("app.services.rag.query.get_settings", return_value=mock_settings),
        patch("app.services.rag.delete_document.get_settings", return_value=mock_settings),
        patch("app.services.rag.list_documents.get_settings", return_value=mock_settings),
    ):
        yield mock_settings


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_patch_settings")
async def test_upload_chunks_and_upserts(mock_qdrant_client):
    """Verify that upload splits text, embeds it, and upserts with correct payload."""
    # We need to return as many vectors as there are chunks.
    # Patch the embeddings to echo back one vector per input.
    with patch("app.services.rag.upload_document.GoogleGenerativeAIEmbeddings") as MockEmbeddings:
        instance = MockEmbeddings.return_value
        instance.aembed_documents = AsyncMock(
            side_effect=lambda texts: [[0.1] * 768 for _ in texts]
        )

        from app.services.rag.upload_document import upload_document

        content = "# Title\n\n" + ("Lorem ipsum dolor sit amet. " * 30)
        result = await upload_document(
            mock_qdrant_client, RagNamespace.MEANING_MAP_DOCS, "test.md", content
        )

    assert result.filename == "test.md"
    assert result.namespace == "meaning-map-docs"
    assert result.chunk_count > 0
    assert result.doc_id  # non-empty UUID

    # Verify upsert was called
    mock_qdrant_client.upsert.assert_called_once()
    call_kwargs = mock_qdrant_client.upsert.call_args
    points = call_kwargs.kwargs.get("points") or call_kwargs[1].get("points")
    assert len(points) == result.chunk_count

    # Verify payload structure
    payload = points[0].payload
    assert payload["namespace"] == "meaning-map-docs"
    assert payload["filename"] == "test.md"
    assert "doc_id" in payload
    assert "chunk_index" in payload
    assert "text" in payload
    assert "uploaded_at" in payload


@pytest.mark.usefixtures("_patch_settings")
async def test_upload_rejects_non_md(mock_qdrant_client):
    """Non-.md files should raise ValueError."""
    from app.services.rag.upload_document import upload_document

    with pytest.raises(ValueError, match=r"Only \.md files"):
        await upload_document(
            mock_qdrant_client, RagNamespace.MEANING_MAP_DOCS, "readme.txt", "content"
        )


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_patch_settings")
async def test_query_filters_by_namespace(mock_qdrant_client):
    """Verify the search call filters by namespace and passes results to LLM."""
    fake_query_vector = [0.5] * 768

    # Mock a search result
    mock_point = MagicMock()
    mock_point.payload = {
        "namespace": "meaning-map-docs",
        "filename": "test.md",
        "chunk_index": 0,
        "text": "The stack uses FastAPI.",
    }
    mock_point.score = 0.95

    mock_result = MagicMock()
    mock_result.points = [mock_point]
    mock_qdrant_client.query_points = AsyncMock(return_value=mock_result)

    with (
        patch("app.services.rag.query.GoogleGenerativeAIEmbeddings") as MockEmb,
        patch("app.services.rag.query.ChatGoogleGenerativeAI") as MockLLM,
    ):
        MockEmb.return_value.aembed_query = AsyncMock(return_value=fake_query_vector)

        mock_response = MagicMock()
        mock_response.content = "The project uses FastAPI as its web framework."
        MockLLM.return_value.ainvoke = AsyncMock(return_value=mock_response)

        from app.services.rag.query import query

        result = await query(
            mock_qdrant_client, RagNamespace.MEANING_MAP_DOCS, "What stack?", top_k=3
        )

    assert result.answer == "The project uses FastAPI as its web framework."
    assert len(result.sources) == 1
    assert result.sources[0].filename == "test.md"
    assert result.sources[0].score == 0.95

    # Verify search was called with namespace filter
    mock_qdrant_client.query_points.assert_called_once()
    call_kwargs = mock_qdrant_client.query_points.call_args
    query_filter = call_kwargs.kwargs.get("query_filter") or call_kwargs[1].get("query_filter")
    assert query_filter is not None


@pytest.mark.usefixtures("_patch_settings")
async def test_query_empty_collection(mock_qdrant_client):
    """When no documents match, return a graceful empty response."""
    mock_result = MagicMock()
    mock_result.points = []
    mock_qdrant_client.query_points = AsyncMock(return_value=mock_result)

    with patch("app.services.rag.query.GoogleGenerativeAIEmbeddings") as MockEmb:
        MockEmb.return_value.aembed_query = AsyncMock(return_value=[0.1] * 768)

        from app.services.rag.query import query

        result = await query(mock_qdrant_client, RagNamespace.MEANING_MAP_DOCS, "Any question?")

    assert "don't have enough information" in result.answer.lower()
    assert result.sources == []


# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_patch_settings")
async def test_delete_uses_namespace_and_doc_id(mock_qdrant_client):
    """Verify delete filters by both namespace and doc_id."""
    # Mock scroll to return 3 existing points
    mock_points = [MagicMock() for _ in range(3)]
    mock_qdrant_client.scroll = AsyncMock(return_value=(mock_points, None))

    from app.services.rag.delete_document import delete_document

    doc_id = str(uuid.uuid4())
    deleted = await delete_document(mock_qdrant_client, RagNamespace.MEANING_MAP_DOCS, doc_id)

    assert deleted == 3
    mock_qdrant_client.delete.assert_called_once()

    # Verify the filter includes both namespace and doc_id
    call_kwargs = mock_qdrant_client.delete.call_args
    points_selector = call_kwargs.kwargs.get("points_selector") or call_kwargs[1].get(
        "points_selector"
    )
    conditions = points_selector.must
    field_names = {c.key for c in conditions}
    assert "namespace" in field_names
    assert "doc_id" in field_names


# ---------------------------------------------------------------------------
# List tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_patch_settings")
async def test_list_groups_by_doc_id(mock_qdrant_client):
    """Points from two documents should produce two DocumentInfo items."""
    doc_id_1 = str(uuid.uuid4())
    doc_id_2 = str(uuid.uuid4())

    points = []
    for doc_id, filename, count in [(doc_id_1, "a.md", 3), (doc_id_2, "b.md", 2)]:
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

    mock_qdrant_client.scroll = AsyncMock(return_value=(points, None))

    from app.services.rag.list_documents import list_documents

    result = await list_documents(mock_qdrant_client, RagNamespace.MEANING_MAP_DOCS)

    assert len(result) == 2
    by_id = {d.doc_id: d for d in result}
    assert by_id[doc_id_1].chunk_count == 3
    assert by_id[doc_id_1].filename == "a.md"
    assert by_id[doc_id_2].chunk_count == 2


@pytest.mark.usefixtures("_patch_settings")
async def test_list_empty_namespace(mock_qdrant_client):
    """Empty namespace should return an empty list."""
    mock_qdrant_client.scroll = AsyncMock(return_value=([], None))

    from app.services.rag.list_documents import list_documents

    result = await list_documents(mock_qdrant_client, RagNamespace.MEANING_MAP_DOCS)
    assert result == []
