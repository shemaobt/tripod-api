from __future__ import annotations

from typing import Any

from app.services.bhsa import loader as bhsa_loader
from app.services.bhsa.reference import normalize_book_name
from app.services.book_context.generation.bhsa_common_nouns import (
    extract_common_noun_candidates,
)
from app.services.book_context.generation.bhsa_entities import extract_bhsa_entities
from app.services.book_context.generation.bhsa_summary import build_bhsa_summary
from app.services.book_context.generation.state import BCDGenerationState


def collect_bhsa(state: BCDGenerationState) -> dict[str, Any]:
    if not bhsa_loader.get_status().is_loaded:
        raise RuntimeError("BHSA data is not loaded. Cannot generate Book Context.")

    tf_api = bhsa_loader._tf_api
    book_name = normalize_book_name(state["book_name"])
    chapter_count = state["chapter_count"]

    summary = build_bhsa_summary(tf_api, book_name, chapter_count)
    if not summary.strip():
        raise RuntimeError(
            f"BHSA returned empty summary for {book_name}. Check book name and chapter count."
        )

    entities = extract_bhsa_entities(tf_api, book_name, chapter_count)
    bhsa_entities = entities["bhsa_entities"]

    if not bhsa_entities:
        raise RuntimeError(
            f"BHSA found no named entities for {book_name}. Cannot build participant register."
        )

    common_nouns = extract_common_noun_candidates(tf_api, book_name, chapter_count)

    return {
        "bhsa_summary": summary,
        "bhsa_entities": bhsa_entities,
        "bhsa_common_nouns": common_nouns["bhsa_common_nouns"],
    }
