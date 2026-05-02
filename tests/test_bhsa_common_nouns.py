from typing import Any

import pytest

from app.services.book_context.generation import bhsa_collection, bhsa_common_nouns


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
    # Use 10 chapters so the adaptive threshold is 2 (default).
    # Single-occurrence lemmas in books >4 chapters must be filtered out.
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
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Genesis", 10)
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
    n_lemmas = bhsa_collection._TOP_N + 50
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
    assert len(result["bhsa_common_nouns"]) == bhsa_collection._TOP_N


def test_includes_adjectives_with_valid_function(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "chapter": 1,
            "verse_count": 2,
            "clauses": [
                {
                    "verse": 1,
                    "content_words": [_content("יהודי", "adjv", gloss="Jewish", function="Subj")],
                },
                {
                    "verse": 2,
                    "content_words": [_content("יהודי", "adjv", gloss="Jewish", function="Cmpl")],
                },
            ],
        }
    ]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Esther", 1)
    candidates = result["bhsa_common_nouns"]
    assert len(candidates) == 1
    assert candidates[0]["lemma"] == "יהודי"
    assert candidates[0]["sp"] == "adjv"
    assert candidates[0]["appearance_count"] == 2


def test_excludes_adjective_only_in_adjunct(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "chapter": 1,
            "verse_count": 2,
            "clauses": [
                {
                    "verse": 1,
                    "content_words": [_content("גדול", "adjv", gloss="great", function="Adju")],
                },
                {
                    "verse": 2,
                    "content_words": [_content("גדול", "adjv", gloss="great", function="Time")],
                },
            ],
        }
    ]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 1)
    assert result["bhsa_common_nouns"] == []


def test_sample_appears_in_caps_at_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    n_appearances = bhsa_collection._SAMPLE_LIMIT + 4
    clauses = [
        {
            "verse": v,
            "content_words": [_content("דבר", "subs", gloss="word", function="Objc")],
        }
        for v in range(1, n_appearances + 1)
    ]
    payload = [{"chapter": 1, "verse_count": n_appearances, "clauses": clauses}]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 1)
    cand = result["bhsa_common_nouns"][0]
    assert cand["appearance_count"] == n_appearances
    assert len(cand["sample_appears_in"]) == bhsa_collection._SAMPLE_LIMIT
    assert cand["sample_appears_in"][0] == {"chapter": 1, "verse": 1}


def _ruth_like_payload() -> list[dict[str, Any]]:
    """Mock BHSA stream covering the critical Ruth lemmas reported in ENG-13.

    Produces multi-occurrence content_words for: שׂדה (field), נעל (sandal),
    שׁער (gate), גאל as a substantive (kinsman-redeemer) and גאל as a verb
    (to redeem). Each lemma appears in ≥2 verses with valid syntactic
    functions so the extractor's filters retain them.
    """
    occurrences: list[tuple[int, int, dict[str, Any]]] = [
        (1, 6, _content("שׂדה", "subs", gloss="open field", function="Cmpl")),
        (2, 2, _content("שׂדה", "subs", gloss="open field", function="Cmpl")),
        (2, 3, _content("שׂדה", "subs", gloss="open field", function="Subj")),
        (4, 7, _content("נעל", "subs", gloss="sandal", function="Objc")),
        (4, 8, _content("נעל", "subs", gloss="sandal", function="Cmpl")),
        (4, 1, _content("שׁער", "subs", gloss="gate", function="Cmpl")),
        (4, 11, _content("שׁער", "subs", gloss="gate", function="Cmpl")),
        (3, 12, _content("גאל", "subs", gloss="redeemer", function="Subj")),
        (4, 1, _content("גאל", "subs", gloss="redeemer", function="Subj")),
        (4, 4, _content("גאל", "verb", gloss="redeem", function="Pred", binyan="qal")),
        (4, 6, _content("גאל", "verb", gloss="redeem", function="Pred", binyan="qal")),
    ]
    by_chapter: dict[int, list[dict[str, Any]]] = {}
    for ch, v, cw in occurrences:
        by_chapter.setdefault(ch, []).append({"verse": v, "content_words": [cw]})
    return [
        {"chapter": ch, "verse_count": max(c["verse"] for c in clauses), "clauses": clauses}
        for ch, clauses in sorted(by_chapter.items())
    ]


def test_ruth_critical_lemmas_are_captured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(_ruth_like_payload()))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Ruth", 4)
    by_key = {(c["lemma"], c["sp"]): c for c in result["bhsa_common_nouns"]}
    assert ("שׂדה", "subs") in by_key, "field (שׂדה) must be captured"
    assert ("נעל", "subs") in by_key, "sandal (נעל) must be captured"
    assert ("שׁער", "subs") in by_key, "gate (שׁער) must be captured"
    assert ("גאל", "subs") in by_key, "kinsman-redeemer (גאל subs) must be captured"
    assert ("גאל", "verb") in by_key, "redeem (גאל verb) must be captured separately"


def test_esther_low_frequency_lemma_survives_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression for the original top-80 cap that dropped שׁרביט (4 occurrences) in Esther."""
    clauses: list[dict[str, Any]] = []
    verse = 1
    # 100 high-frequency dummy lemmas (5 occurrences each) — far below the 250 cap.
    for i in range(100):
        for _ in range(5):
            clauses.append(
                {
                    "verse": verse,
                    "content_words": [
                        _content(f"dummy{i}", "subs", gloss=f"d{i}", function="Subj"),
                    ],
                }
            )
            verse += 1
    # The scepter only has 4 occurrences — must still survive.
    for _ in range(4):
        clauses.append(
            {
                "verse": verse,
                "content_words": [_content("שׁרביט", "subs", gloss="staff", function="Objc")],
            }
        )
        verse += 1
    payload = [{"chapter": 1, "verse_count": verse - 1, "clauses": clauses}]
    monkeypatch.setattr(bhsa_common_nouns, "stream_book_clauses", _stream(payload))
    result = bhsa_common_nouns.extract_common_noun_candidates(None, "Esther", 1)
    lemmas = {c["lemma"] for c in result["bhsa_common_nouns"]}
    assert "שׁרביט" in lemmas, "scepter must survive the cap when total candidates < _TOP_N"
