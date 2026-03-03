from __future__ import annotations

from typing import Any

from app.services.bhsa.clause import extract_clause
from app.services.bhsa.reference import parse_reference

_CLAUSE_OTYPE = "clause"


def extract_passage(tf_api: Any, ref: str) -> dict[str, Any]:
    book, chapter, start_verse, end_verse = parse_reference(ref)
    return _extract_verses(tf_api, book, chapter, start_verse, end_verse)


def _extract_verses(
    tf_api: Any,
    book: str,
    chapter: int,
    start_verse: int,
    end_verse: int,
) -> dict[str, Any]:
    F = tf_api.api.F
    L = tf_api.api.L
    T = tf_api.api.T

    clauses: list[dict[str, Any]] = []
    clause_id = 1
    prev_type: str | None = None
    actual_end = start_verse

    for verse_num in range(start_verse, end_verse + 1):
        try:
            verse_node = T.nodeFromSection((book, chapter, verse_num))
        except Exception:
            if verse_num == start_verse:
                raise ValueError(f"Could not find {book} {chapter}:{verse_num}") from None
            break

        actual_end = verse_num
        for clause_node in L.d(verse_node, otype=_CLAUSE_OTYPE):
            data = extract_clause(clause_node, verse_num, clause_id, prev_type, F, L, T)
            clauses.append(data)
            clause_id += 1
            prev_type = data["clause_type"]

    if start_verse == actual_end:
        ref_str = f"{book} {chapter}:{start_verse}"
    else:
        ref_str = f"{book} {chapter}:{start_verse}-{actual_end}"

    return {
        "reference": ref_str,
        "source_lang": "hbo",
        "clauses": clauses,
    }
