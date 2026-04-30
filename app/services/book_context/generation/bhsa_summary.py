from __future__ import annotations

from typing import Any

from app.services.book_context.generation.bhsa_collection import BHSASummaryBuilder
from app.services.book_context.generation.bhsa_stream import stream_book_clauses


def build_bhsa_summary(tf_api: Any, book_name: str, chapter_count: int) -> str:
    builder = BHSASummaryBuilder()
    for chapter_data in stream_book_clauses(tf_api, book_name, chapter_count):
        ch = chapter_data["chapter"]
        builder.start_chapter(ch)
        for clause in chapter_data["clauses"]:
            builder.consume(ch, clause)
    return builder.build()
