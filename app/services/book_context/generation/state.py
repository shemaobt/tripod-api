from typing import TypedDict


class BCDGenerationState(TypedDict, total=False):
    book_name: str
    book_id: str
    bcd_id: str
    genre: str
    chapter_count: int
    bhsa_summary: str
    bhsa_entities: list
    structural_outline: dict
    participant_register: list
    discourse_threads: list
    theological_spine: str
    places: list
    objects: list
    institutions: list
    genre_context: dict
    maintenance_notes: dict
    user_feedback: str
