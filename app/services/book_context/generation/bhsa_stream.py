from __future__ import annotations

from collections.abc import Generator
from typing import Any

from app.services.bhsa.clause import extract_clause
from app.services.book_context.generation.types import ClauseExtract


def stream_book_clauses(
    tf_api: Any,
    book_name: str,
    chapter_count: int,
) -> Generator[dict[str, Any], None, None]:
    T = tf_api.api.T
    F = tf_api.api.F
    L = tf_api.api.L

    for chapter in range(1, chapter_count + 1):
        clauses: list[ClauseExtract] = []
        clause_id = 1
        prev_type: str | None = None

        verse_num = 1
        while True:
            try:
                verse_node = T.nodeFromSection((book_name, chapter, verse_num))
            except (KeyError, ValueError, TypeError):
                break
            if verse_node is None:
                break

            for clause_node in L.d(verse_node, otype="clause"):
                data = extract_clause(clause_node, verse_num, clause_id, prev_type, F, L, T)
                clauses.append(data)
                clause_id += 1
                prev_type = data["clause_type"]

            verse_num += 1

        yield {
            "chapter": chapter,
            "verse_count": verse_num - 1,
            "clauses": clauses,
        }
