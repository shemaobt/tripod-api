from typing import Any

import pytest

from app.services.book_context.generation import (
    bhsa_collection,
    bhsa_common_nouns,
    bhsa_entities,
    bhsa_summary,
)
from app.services.book_context.generation.bhsa_collection import (
    BHSACommonNounsBuilder,
    BHSAEntitiesBuilder,
    BHSASummaryBuilder,
    _min_appearances_for,
    collect_bhsa_data,
)


def _stream(payload: list[dict[str, Any]]):
    def _fake_stream(_tf_api, _book_name, _chapter_count):
        yield from payload

    return _fake_stream


def _clause(
    verse: int,
    *,
    text: str = "",
    gloss: str = "",
    lemma: str | None = None,
    binyan: str | None = None,
    tense: str | None = None,
    names: list[str] | None = None,
    name_glosses: dict[str, str] | None = None,
    name_types: dict[str, str] | None = None,
    content_words: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "clause_id": verse,
        "verse": verse,
        "text": text,
        "gloss": gloss,
        "clause_type": "Way0",
        "is_mainline": True,
        "chain_position": "initial",
        "lemma": lemma,
        "lemma_ascii": lemma,
        "binyan": binyan,
        "tense": tense,
        "subjects": [],
        "objects": [],
        "has_ki": False,
        "names": names or [],
        "name_glosses": name_glosses or {},
        "name_types": name_types or {},
        "content_words": content_words or [],
    }


def _cw(
    lex_utf8: str,
    sp: str,
    *,
    gloss: str = "",
    function: str | None = None,
    binyan: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "lex_utf8": lex_utf8,
        "lex": lex_utf8,
        "sp": sp,
        "gloss": gloss,
        "pdp": None,
        "function": function,
    }
    if binyan:
        entry["binyan"] = binyan
    return entry


def test_summary_builder_emits_chapter_header_with_clause_count() -> None:
    builder = BHSASummaryBuilder()
    builder.start_chapter(1)
    builder.consume(1, _clause(1, gloss="went out"))
    builder.consume(1, _clause(2, gloss="returned"))
    out = builder.build()
    assert "=== Chapter 1 (2 clauses) ===" in out
    assert "v1: went out" in out
    assert "v2: returned" in out


def test_summary_builder_aggregates_names_and_verbs() -> None:
    builder = BHSASummaryBuilder()
    builder.start_chapter(1)
    builder.consume(1, _clause(1, lemma="HLK", binyan="qal", tense="wayq", names=["Naomi"]))
    builder.consume(1, _clause(2, lemma="ŠWB", binyan="qal", tense="wayq"))
    out = builder.build()
    assert "Names: Naomi" in out
    assert "HLK (qal/wayq)" in out
    assert "ŠWB (qal/wayq)" in out


def test_summary_builder_resets_per_chapter() -> None:
    builder = BHSASummaryBuilder()
    builder.start_chapter(1)
    builder.consume(1, _clause(1, names=["Naomi"]))
    builder.start_chapter(2)
    builder.consume(2, _clause(1, names=["Boaz"]))
    out = builder.build()
    assert "=== Chapter 1 (1 clauses) ===" in out
    assert "=== Chapter 2 (1 clauses) ===" in out
    # Boaz should appear only in chapter 2 block
    chapter1, chapter2 = out.split("=== Chapter 2")
    assert "Boaz" not in chapter1
    assert "Boaz" in chapter2


def test_entities_builder_aggregates_appearances() -> None:
    builder = BHSAEntitiesBuilder()
    builder.consume(
        1,
        _clause(
            1,
            names=["Naomi"],
            name_glosses={"Naomi": "Naomi"},
            name_types={"Naomi": "pers"},
        ),
    )
    builder.consume(1, _clause(5, names=["Naomi"]))
    builder.consume(2, _clause(3, names=["Naomi", "Ruth"], name_types={"Ruth": "pers"}))
    entities = builder.build()
    naomi = next(e for e in entities if e["name"] == "Naomi")
    assert naomi["entry_verse"] == {"chapter": 1, "verse": 1}
    assert naomi["exit_verse"] == {"chapter": 2, "verse": 3}
    assert naomi["appearance_count"] == 3
    assert naomi["entity_type"] == "person"


def test_entities_builder_skips_mens_nametype() -> None:
    builder = BHSAEntitiesBuilder()
    builder.consume(
        1,
        _clause(1, names=["Foo"], name_types={"Foo": "mens"}),
    )
    assert builder.build() == []


def test_common_nouns_builder_filters_low_frequency() -> None:
    builder = BHSACommonNounsBuilder()
    builder.consume(1, _clause(1, content_words=[_cw("rare", "subs", function="Subj")]))
    assert builder.build() == []


def test_common_nouns_builder_accepts_min_appearances_override() -> None:
    builder = BHSACommonNounsBuilder(min_appearances=1)
    builder.consume(
        1, _clause(1, content_words=[_cw("איפה", "subs", gloss="ephah", function="Objc")])
    )
    candidates = builder.build()
    assert len(candidates) == 1
    assert candidates[0]["lemma"] == "איפה"
    assert candidates[0]["appearance_count"] == 1


def test_min_appearances_for_small_book() -> None:
    assert _min_appearances_for(1) == 1
    assert _min_appearances_for(4) == 1
    assert _min_appearances_for(5) == 2
    assert _min_appearances_for(50) == 2


def test_collect_bhsa_data_uses_adaptive_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """Books with ≤4 chapters accept single-occurrence lemmas (Strategy 1)."""
    payload = [
        {
            "chapter": 1,
            "verse_count": 1,
            "clauses": [
                _clause(
                    1,
                    names=["A"],
                    name_types={"A": "pers"},
                    content_words=[_cw("איפה", "subs", gloss="ephah", function="Objc")],
                ),
            ],
        }
    ]
    monkeypatch.setattr(bhsa_collection, "stream_book_clauses", _stream(payload))

    # 4 chapters → threshold 1 → single-occurrence lemma kept
    result_small = collect_bhsa_data(None, "Ruth", 4)
    assert any(c["lemma"] == "איפה" for c in result_small.bhsa_common_nouns)

    # 50 chapters → threshold 2 → single-occurrence lemma dropped
    monkeypatch.setattr(bhsa_collection, "stream_book_clauses", _stream(payload))
    result_large = collect_bhsa_data(None, "Genesis", 50)
    assert not any(c["lemma"] == "איפה" for c in result_large.bhsa_common_nouns)


def test_common_nouns_builder_includes_verbs_with_any_function() -> None:
    builder = BHSACommonNounsBuilder()
    builder.consume(1, _clause(1, content_words=[_cw("גאל", "verb", binyan="qal")]))
    builder.consume(1, _clause(2, content_words=[_cw("גאל", "verb", binyan="qal")]))
    candidates = builder.build()
    assert len(candidates) == 1
    assert candidates[0]["sp"] == "verb"
    assert candidates[0]["lemma"] == "גאל"
    assert candidates[0]["top_binyans"] == ["qal"]


def test_collect_bhsa_data_runs_single_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "chapter": 1,
            "verse_count": 2,
            "clauses": [
                _clause(
                    1,
                    gloss="went out",
                    lemma="HLK",
                    binyan="qal",
                    tense="wayq",
                    names=["Naomi"],
                    name_types={"Naomi": "pers"},
                    content_words=[_cw("שדה", "subs", gloss="field", function="Cmpl")],
                ),
                _clause(
                    2,
                    gloss="returned",
                    names=["Naomi"],
                    content_words=[_cw("שדה", "subs", gloss="field", function="Subj")],
                ),
            ],
        }
    ]
    call_count = {"n": 0}

    def _counted_stream(_tf_api, _book_name, _chapter_count):
        call_count["n"] += 1
        yield from payload

    monkeypatch.setattr(bhsa_collection, "stream_book_clauses", _counted_stream)
    result = collect_bhsa_data(None, "Ruth", 1)

    assert call_count["n"] == 1
    assert "=== Chapter 1 (2 clauses) ===" in result.bhsa_summary
    assert any(e["name"] == "Naomi" for e in result.bhsa_entities)
    assert any(c["lemma"] == "שדה" for c in result.bhsa_common_nouns)


def test_collect_bhsa_data_matches_legacy_wrappers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = [
        {
            "chapter": 1,
            "verse_count": 2,
            "clauses": [
                _clause(
                    1,
                    gloss="went",
                    lemma="HLK",
                    binyan="qal",
                    tense="wayq",
                    names=["Naomi"],
                    name_glosses={"Naomi": "Naomi"},
                    name_types={"Naomi": "pers"},
                    content_words=[_cw("שדה", "subs", gloss="field", function="Cmpl")],
                ),
                _clause(
                    2,
                    gloss="returned",
                    lemma="ŠWB",
                    binyan="qal",
                    tense="wayq",
                    names=["Naomi"],
                    content_words=[_cw("שדה", "subs", gloss="field", function="Subj")],
                ),
            ],
        }
    ]

    monkeypatch.setattr(bhsa_collection, "stream_book_clauses", _stream(payload))
    monkeypatch.setattr(bhsa_summary, "stream_book_clauses", _stream(payload))
    monkeypatch.setattr(bhsa_entities, "stream_book_clauses", _stream(payload))
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))

    combined = collect_bhsa_data(None, "Ruth", 1)
    legacy_summary = bhsa_summary.build_bhsa_summary(None, "Ruth", 1)
    legacy_entities = bhsa_entities.extract_bhsa_entities(None, "Ruth", 1)["bhsa_entities"]
    legacy_common = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 1)[
        "bhsa_common_nouns"
    ]

    assert combined.bhsa_summary == legacy_summary
    assert combined.bhsa_entities == legacy_entities
    assert combined.bhsa_common_nouns == legacy_common
