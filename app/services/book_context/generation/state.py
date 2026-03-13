from typing import Any, TypedDict


class BCDGenerationState(TypedDict, total=False):
    book_name: str
    book_id: str
    bcd_id: str
    genre: str
    chapter_count: int
    bhsa_summary: str
    bhsa_entities: list[dict[str, Any]]
    structural_outline: dict[str, Any]
    participant_register: list[dict[str, Any]]
    discourse_threads: list[dict[str, Any]]
    theological_spine: str
    places: list[dict[str, Any]]
    objects: list[dict[str, Any]]
    institutions: list[dict[str, Any]]
    genre_context: dict[str, Any]
    maintenance_notes: dict[str, Any]
    user_feedback: str
