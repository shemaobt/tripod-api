from unittest.mock import MagicMock

import pytest

from app.services.bhsa import loader
from app.services.bhsa.clause import get_chain_position, is_mainline
from app.services.bhsa.passage import extract_passage
from app.services.bhsa.reference import normalize_book_name, parse_reference


@pytest.mark.asyncio
async def test_parse_verse_range() -> None:
    assert parse_reference("Ruth 1:1-6") == ("Ruth", 1, 1, 6)


@pytest.mark.asyncio
async def test_parse_single_verse() -> None:
    assert parse_reference("Gen 1:1") == ("Genesis", 1, 1, 1)


@pytest.mark.asyncio
async def test_parse_with_abbreviation() -> None:
    assert parse_reference("Ps 23:1-3") == ("Psalms", 23, 1, 3)


@pytest.mark.asyncio
async def test_parse_numbered_book() -> None:
    assert parse_reference("1 Samuel 3:1-4") == ("1_Samuel", 3, 1, 4)


@pytest.mark.asyncio
async def test_parse_en_dash_range() -> None:
    assert parse_reference("Ruth 1:1\u20135") == ("Ruth", 1, 1, 5)


@pytest.mark.asyncio
async def test_parse_invalid_reference() -> None:
    with pytest.raises(ValueError, match="Could not parse"):
        parse_reference("invalid")


@pytest.mark.asyncio
async def test_normalize_exact_match() -> None:
    assert normalize_book_name("genesis") == "Genesis"


@pytest.mark.asyncio
async def test_normalize_abbreviation() -> None:
    assert normalize_book_name("deut") == "Deuteronomy"


@pytest.mark.asyncio
async def test_normalize_fuzzy_match() -> None:
    assert normalize_book_name("genesi") == "Genesis"


@pytest.mark.asyncio
async def test_normalize_unrecognized() -> None:
    assert normalize_book_name("Unknown") == "Unknown"


@pytest.mark.asyncio
async def test_is_mainline() -> None:
    assert is_mainline("Way0") is True
    assert is_mainline("WayX") is True
    assert is_mainline("NmCl") is False


@pytest.mark.asyncio
async def test_chain_position_initial() -> None:
    assert get_chain_position("Way0", None) == "initial"
    assert get_chain_position("Way0", "NmCl") == "initial"


@pytest.mark.asyncio
async def test_chain_position_continuation() -> None:
    assert get_chain_position("WayX", "Way0") == "continuation"


@pytest.mark.asyncio
async def test_chain_position_break() -> None:
    assert get_chain_position("NmCl", "Way0") == "break"


@pytest.mark.asyncio
async def test_fetch_passage_not_loaded_raises() -> None:
    with pytest.raises(RuntimeError, match="BHSA not loaded"):
        loader.fetch_passage("Ruth 1:1-6")


def _build_mock_tf_api() -> MagicMock:
    mock_word = MagicMock()
    mock_clause = MagicMock()
    mock_verse = MagicMock()

    F = MagicMock()
    F.typ.v.return_value = "Way0"
    F.sp.v.return_value = "verb"
    F.lex.v.return_value = "HLK/"
    F.lex_utf8.v.return_value = "הלך"
    F.vs.v.return_value = "qal"
    F.vt.v.return_value = "wayq"
    F.gloss.v.return_value = "walk"
    F.function.v.return_value = "Pred"

    L = MagicMock()
    L.d.side_effect = lambda node, otype=None: {
        "clause": [mock_clause],
        "word": [mock_word],
        "phrase": [],
    }.get(otype, [])

    T = MagicMock()
    T.nodeFromSection.return_value = mock_verse
    T.text.return_value = "וַיֵּ֥לֶךְ"

    api = MagicMock()
    api.api.F = F
    api.api.L = L
    api.api.T = T
    return api


@pytest.mark.asyncio
async def test_extract_passage_returns_clauses() -> None:
    tf_api = _build_mock_tf_api()
    result = extract_passage(tf_api, "Ruth 1:1")

    assert result["reference"] == "Ruth 1:1"
    assert result["source_lang"] == "hbo"
    assert len(result["clauses"]) == 1

    clause = result["clauses"][0]
    assert clause["clause_id"] == 1
    assert clause["verse"] == 1
    assert clause["clause_type"] == "Way0"
    assert clause["is_mainline"] is True
    assert clause["gloss"] == "walk"
