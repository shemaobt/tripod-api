from __future__ import annotations

from typing import Any

from app.services.book_context.generation.bhsa_collection import BHSAEntitiesBuilder
from app.services.book_context.generation.bhsa_stream import stream_book_clauses
from app.services.book_context.generation.types import BHSAEntity


def extract_bhsa_entities(
    tf_api: Any, book_name: str, chapter_count: int
) -> dict[str, list[BHSAEntity]]:
    builder = BHSAEntitiesBuilder()
    for chapter_data in stream_book_clauses(tf_api, book_name, chapter_count):
        ch = chapter_data["chapter"]
        for clause in chapter_data["clauses"]:
            builder.consume(ch, clause)
    return {"bhsa_entities": builder.build()}
