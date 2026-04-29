from typing import Any

import pytest

from app.services.book_context.generation import bhsa_common_nouns


def _stream(payload: list[dict[str, Any]]):
    def _fake_stream(_tf_api, _book_name, _chapter_count):
        yield from payload

    return _fake_stream


def _content(
    lex_utf8: str,
    sp: str,
    *,
    gloss: str = "",
    function: str | None = None,
    pdp: str | None = None,
    binyan: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "lex_utf8": lex_utf8,
        "lex": lex_utf8,
        "sp": sp,
        "gloss": gloss,
        "function": function,
        "pdp": pdp,
    }
    if binyan:
        entry["binyan"] = binyan
    return entry


def test_filters_lemmas_below_min_appearances(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "chapter": 1,
            "verse_count": 1,
            "clauses": [
                {
                    "verse": 1,
                    "content_words": [_content("שדה", "subs", gloss="field", function="Cmpl")],
                }
            ],
        }
    ]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 1)
    assert result["bhsa_common_nouns"] == []


def test_includes_substantives_with_valid_function(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "chapter": 1,
            "verse_count": 2,
            "clauses": [
                {
                    "verse": 1,
                    "content_words": [_content("שדה", "subs", gloss="field", function="Cmpl")],
                },
                {
                    "verse": 2,
                    "content_words": [_content("שדה", "subs", gloss="field", function="Subj")],
                },
            ],
        }
    ]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 1)
    candidates = result["bhsa_common_nouns"]
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["lemma"] == "שדה"
    assert cand["sp"] == "subs"
    assert cand["english_gloss"] == "field"
    assert cand["appearance_count"] == 2
    assert cand["first_appears"] == {"chapter": 1, "verse": 1}
    assert {"chapter": 1, "verse": 1} in cand["sample_appears_in"]
    assert {"chapter": 1, "verse": 2} in cand["sample_appears_in"]


def test_excludes_substantive_only_in_adjunct(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "chapter": 1,
            "verse_count": 2,
            "clauses": [
                {
                    "verse": 1,
                    "content_words": [_content("יום", "subs", gloss="day", function="Adju")],
                },
                {
                    "verse": 2,
                    "content_words": [_content("יום", "subs", gloss="day", function="Time")],
                },
            ],
        }
    ]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 1)
    assert result["bhsa_common_nouns"] == []


def test_includes_verbs_regardless_of_function(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "chapter": 1,
            "verse_count": 2,
            "clauses": [
                {
                    "verse": 1,
                    "content_words": [
                        _content("גאל", "verb", gloss="redeem", function="Pred", binyan="qal"),
                    ],
                },
                {
                    "verse": 2,
                    "content_words": [
                        _content("גאל", "verb", gloss="redeem", function="Pred", binyan="qal"),
                    ],
                },
            ],
        }
    ]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 1)
    candidates = result["bhsa_common_nouns"]
    assert len(candidates) == 1
    assert candidates[0]["sp"] == "verb"
    assert candidates[0]["top_binyans"] == ["qal"]


def test_separate_buckets_for_same_lemma_with_different_sp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = [
        {
            "chapter": 1,
            "verse_count": 4,
            "clauses": [
                {
                    "verse": 1,
                    "content_words": [
                        _content("גאל", "subs", gloss="kinsman", function="Subj"),
                    ],
                },
                {
                    "verse": 2,
                    "content_words": [
                        _content("גאל", "subs", gloss="kinsman", function="Subj"),
                    ],
                },
                {
                    "verse": 3,
                    "content_words": [
                        _content("גאל", "verb", gloss="redeem", function="Pred", binyan="qal"),
                    ],
                },
                {
                    "verse": 4,
                    "content_words": [
                        _content("גאל", "verb", gloss="redeem", function="Pred", binyan="qal"),
                    ],
                },
            ],
        }
    ]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 1)
    candidates = {(c["lemma"], c["sp"]) for c in result["bhsa_common_nouns"]}
    assert ("גאל", "subs") in candidates
    assert ("גאל", "verb") in candidates


def test_top_n_truncates_results(monkeypatch: pytest.MonkeyPatch) -> None:
    n_lemmas = bhsa_common_nouns._TOP_N + 50
    clauses = []
    for i in range(n_lemmas):
        lex = f"lex{i}"
        clauses.append(
            {
                "verse": (i * 2) + 1,
                "content_words": [
                    _content(lex, "subs", gloss=f"g{i}", function="Subj"),
                ],
            }
        )
        clauses.append(
            {
                "verse": (i * 2) + 2,
                "content_words": [
                    _content(lex, "subs", gloss=f"g{i}", function="Subj"),
                ],
            }
        )
    payload = [{"chapter": 1, "verse_count": n_lemmas * 2, "clauses": clauses}]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 1)
    assert len(result["bhsa_common_nouns"]) == bhsa_common_nouns._TOP_N
