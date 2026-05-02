from __future__ import annotations

from typing import Any

from app.services.book_context.generation.bhsa_collection import (
    BHSACommonNounsBuilder,
    _min_appearances_for,
)
from app.services.book_context.generation.bhsa_stream import stream_book_clauses
from app.services.book_context.generation.types import CommonNounCandidate

__all__ = ["extract_common_noun_candidates"]


def extract_common_noun_candidates(
    tf_api: Any, book_name: str, chapter_count: int
) -> dict[str, list[CommonNounCandidate]]:
    builder = BHSACommonNounsBuilder(min_appearances=_min_appearances_for(chapter_count))
    for chapter_data in stream_book_clauses(tf_api, book_name, chapter_count):
        ch = chapter_data["chapter"]
        for clause in chapter_data["clauses"]:
            builder.consume(ch, clause)
    return {"bhsa_common_nouns": builder.build()}
