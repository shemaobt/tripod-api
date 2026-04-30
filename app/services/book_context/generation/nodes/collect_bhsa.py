from __future__ import annotations

from app.services.bhsa import loader as bhsa_loader
from app.services.bhsa.reference import normalize_book_name
from app.services.book_context.generation.bhsa_collection import collect_bhsa_data
from app.services.book_context.generation.state import BCDGenerationState
from app.services.book_context.generation.types import CollectBHSAOutput


def collect_bhsa(state: BCDGenerationState) -> CollectBHSAOutput:
    if not bhsa_loader.get_status().is_loaded:
        raise RuntimeError("BHSA data is not loaded. Cannot generate Book Context.")

    tf_api = bhsa_loader._tf_api
    book_name = normalize_book_name(state["book_name"])
    chapter_count = state["chapter_count"]

    result = collect_bhsa_data(tf_api, book_name, chapter_count)

    if not result["bhsa_summary"].strip():
        raise RuntimeError(
            f"BHSA returned empty summary for {book_name}. Check book name and chapter count."
        )
    if not result["bhsa_entities"]:
        raise RuntimeError(
            f"BHSA found no named entities for {book_name}. Cannot build participant register."
        )

    return result
