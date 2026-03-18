from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.db.models.meaning_map import MeaningMapStatus, Testament


class PMMPerson(BaseModel):
    name: str
    role: str
    relationship: str
    wants: str
    carries: str


class PMMPlace(BaseModel):
    name: str
    role: str
    type: str
    meaning: str
    effect_on_scene: str


class PMMObject(BaseModel):
    name: str
    what_it_is: str
    function_in_scene: str
    signals: str


class PMMScene(BaseModel):
    scene_number: int
    verses: str
    title: str
    people: list[PMMPerson]
    places: list[PMMPlace]
    objects: list[PMMObject]
    significant_absence: str
    what_happens: str
    communicative_purpose: str


class PMMQAPair(BaseModel):
    question: str
    answer: str


class PMMProposition(BaseModel):
    proposition_number: int
    verse: str
    content: list[PMMQAPair]


class PMMLevel1(BaseModel):
    arc: str


class ProseMeaningMap(BaseModel):
    level_1: PMMLevel1
    level_2_scenes: list[PMMScene]
    level_3_propositions: list[PMMProposition]


class BibleBookResponse(BaseModel):
    id: str
    name: str
    abbreviation: str
    testament: Testament
    order: int
    chapter_count: int
    is_enabled: bool
    pericope_count: int = 0
    approved_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ChapterSummary(BaseModel):
    chapter: int
    pericope_count: int = 0
    draft_count: int = 0
    cross_check_count: int = 0
    approved_count: int = 0


class PericopeCreate(BaseModel):
    book_id: str
    chapter_start: int = Field(ge=1)
    verse_start: int = Field(ge=1)
    chapter_end: int = Field(ge=1)
    verse_end: int = Field(ge=1)
    reference: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=300)


class PericopeResponse(BaseModel):
    id: str
    book_id: str
    chapter_start: int
    verse_start: int
    chapter_end: int
    verse_end: int
    reference: str
    title: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PericopeWithStatusResponse(PericopeResponse):
    meaning_map_id: str | None = None
    status: MeaningMapStatus | None = None
    locked_by: str | None = None
    locked_by_name: str | None = None
    analyst_name: str | None = None
    unresolved_feedback_count: int = 0


class MeaningMapCreate(BaseModel):
    pericope_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class MeaningMapGenerateRequest(BaseModel):
    pericope_id: str


class MeaningMapUpdateData(BaseModel):
    data: dict[str, Any]


class MeaningMapStatusUpdate(BaseModel):
    status: MeaningMapStatus


class MeaningMapListResponse(BaseModel):
    id: str
    pericope_id: str
    analyst_id: str
    cross_checker_id: str | None
    status: MeaningMapStatus
    version: int
    locked_by: str | None
    locked_at: datetime | None
    date_approved: datetime | None
    approved_by: str | None
    created_at: datetime
    updated_at: datetime
    book_id: str | None = None
    book_name: str | None = None
    pericope_reference: str | None = None

    model_config = {"from_attributes": True}


class MeaningMapResponse(MeaningMapListResponse):
    data: dict[str, Any]
    translations: dict[str, Any] | None = None


class AnalystSummary(BaseModel):
    name: str
    assigned: int
    draft: int
    cross_check: int
    approved: int


class DashboardSummaryResponse(BaseModel):
    total: int
    draft: int
    cross_check: int
    approved: int
    unstarted: int
    enabled_books: int
    analysts: list[AnalystSummary]


class FeedbackCreate(BaseModel):
    section_key: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class FeedbackUpdate(BaseModel):
    resolved: bool


class FeedbackResponse(BaseModel):
    id: str
    meaning_map_id: str
    section_key: str
    author_id: str
    author_name: str | None = None
    content: str
    resolved: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
