import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.meaning_map.generator import (
    _build_generation_prompt,
    _empty_map,
    _parse_llm_output,
    generate_meaning_map,
)

VALID_MAP = {
    "level_1": {"arc": "Test arc"},
    "level_2_scenes": [],
    "level_3_propositions": [],
}


# ---------------------------------------------------------------------------
# _parse_llm_output
# ---------------------------------------------------------------------------


def test_parse_llm_output_valid_json() -> None:
    raw = json.dumps(VALID_MAP)
    result = _parse_llm_output(raw)
    assert result == VALID_MAP


def test_parse_llm_output_markdown_fenced() -> None:
    raw = f"```json\n{json.dumps(VALID_MAP)}\n```"
    result = _parse_llm_output(raw)
    assert result == VALID_MAP


def test_parse_llm_output_invalid_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_llm_output("not json at all")


# ---------------------------------------------------------------------------
# _empty_map
# ---------------------------------------------------------------------------


def test_empty_map_structure() -> None:
    result = _empty_map()
    assert "level_1" in result
    assert result["level_1"]["arc"] == ""
    assert result["level_2_scenes"] == []
    assert result["level_3_propositions"] == []


# ---------------------------------------------------------------------------
# _build_generation_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_includes_reference() -> None:
    prompt = _build_generation_prompt("Genesis 1:1-5", None, None)
    assert "Genesis 1:1-5" in prompt


def test_build_prompt_includes_bhsa_data() -> None:
    bhsa_data = {
        "clauses": [{"text_plain": "bereshit", "clause_type": "NC", "gloss": "in the beginning"}]
    }
    prompt = _build_generation_prompt("Genesis 1:1", bhsa_data, None)
    assert "Hebrew Linguistic Data" in prompt
    assert "bereshit" in prompt
    assert "in the beginning" in prompt


def test_build_prompt_includes_rag_context() -> None:
    prompt = _build_generation_prompt("Genesis 1:1", None, "Use the Tripod Method steps.")
    assert "Methodology Reference" in prompt
    assert "Use the Tripod Method steps." in prompt


def test_build_prompt_excludes_bhsa_when_none() -> None:
    prompt = _build_generation_prompt("Genesis 1:1", None, None)
    assert "Hebrew Linguistic Data" not in prompt


def test_build_prompt_excludes_rag_when_none() -> None:
    prompt = _build_generation_prompt("Genesis 1:1", None, None)
    assert "Methodology Reference" not in prompt


# ---------------------------------------------------------------------------
# generate_meaning_map
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_settings():
    return SimpleNamespace(
        google_api_key="fake-key",
        google_llm_model="gemini-3.1-pro-preview",
        google_embedding_model="gemini-embedding-001",
        qdrant_collection="test",
        rag_chunk_size=200,
        rag_chunk_overlap=50,
        rag_top_k=3,
    )


@pytest.mark.asyncio
@patch("app.services.meaning_map.generator.bhsa_loader")
@patch("app.services.meaning_map.generator.ChatGoogleGenerativeAI")
async def test_generate_meaning_map_success(mock_llm_cls, mock_bhsa, mock_settings) -> None:
    mock_bhsa.get_status.return_value = {"is_loaded": False}

    response = MagicMock()
    response.content = json.dumps(VALID_MAP)
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=response)
    mock_llm_cls.return_value = mock_llm

    result = await generate_meaning_map("Genesis 1:1-5", settings=mock_settings)
    assert result == VALID_MAP
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.meaning_map.generator.bhsa_loader")
@patch("app.services.meaning_map.generator.ChatGoogleGenerativeAI")
async def test_generate_meaning_map_fallback_on_failure(
    mock_llm_cls, mock_bhsa, mock_settings
) -> None:
    mock_bhsa.get_status.return_value = {"is_loaded": False}

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
    mock_llm_cls.return_value = mock_llm

    result = await generate_meaning_map("Genesis 1:1-5", settings=mock_settings)
    assert result == _empty_map()


@pytest.mark.asyncio
@patch("app.services.meaning_map.generator.rag_query")
@patch("app.services.meaning_map.generator.bhsa_loader")
@patch("app.services.meaning_map.generator.ChatGoogleGenerativeAI")
async def test_generate_meaning_map_with_rag(
    mock_llm_cls, mock_bhsa, mock_rag_query, mock_settings
) -> None:
    mock_bhsa.get_status.return_value = {"is_loaded": False}

    rag_result = MagicMock()
    rag_result.answer = "Use the Tripod Method for OBT."
    mock_rag_query.return_value = rag_result

    response = MagicMock()
    response.content = json.dumps(VALID_MAP)
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=response)
    mock_llm_cls.return_value = mock_llm

    qdrant = AsyncMock()
    result = await generate_meaning_map(
        "Genesis 1:1-5", settings=mock_settings, qdrant_client=qdrant
    )
    assert result == VALID_MAP
    mock_rag_query.assert_called_once()
