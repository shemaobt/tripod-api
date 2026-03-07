from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.db.models.book_context import BCDStatus


class VerseRef(BaseModel):
    chapter: int
    verse: int


class ArcEntry(BaseModel):
    at: VerseRef
    state: str


class EpisodeStatus(BaseModel):
    at: VerseRef
    status: str


class BCDParticipantEntry(BaseModel):
    name: str
    english_gloss: str = ""
    type: Literal["named", "group"]
    entry_verse: VerseRef
    exit_verse: VerseRef | None = None
    role_in_book: str
    relationships: list[str] = Field(default_factory=list)
    what_audience_knows_at_entry: str = ""
    arc: list[ArcEntry] = Field(default_factory=list)
    status_at_end: str = ""


class BCDDiscourseThread(BaseModel):
    label: str
    opened_at: VerseRef
    resolved_at: VerseRef | None = None
    question: str
    status_by_episode: list[EpisodeStatus] = Field(default_factory=list)


class BCDPlace(BaseModel):
    name: str
    english_gloss: str = ""
    first_appears: VerseRef
    type: str = ""
    meaning_and_function: str = ""
    appears_in: list[VerseRef] = Field(default_factory=list)


class BCDObject(BaseModel):
    name: str
    first_appears: VerseRef
    what_it_is: str = ""
    meaning_across_scenes: str = ""
    appears_in: list[VerseRef] = Field(default_factory=list)


class BCDInstitution(BaseModel):
    name: str
    first_invoked: VerseRef
    what_it_is: str = ""
    role_in_book: str = ""
    appears_in: list[VerseRef] = Field(default_factory=list)


class BCDCreateRequest(BaseModel):
    genre: str = Field(min_length=1, max_length=50)
    section_label: str | None = None
    section_range_start: int | None = None
    section_range_end: int | None = None


class BCDGenerateRequest(BaseModel):
    feedback: str | None = Field(None, max_length=2000)


class BCDSectionUpdateRequest(BaseModel):
    data: dict | str | list


class BCDApprovalResponse(BaseModel):
    id: str
    bcd_id: str
    user_id: str
    role_at_approval: str
    roles_at_approval: list[str] = []
    approved_at: datetime

    model_config = {"from_attributes": True}


class BCDApprovalStatusResponse(BaseModel):
    approvals: list[dict]
    covered_specialties: list[str]
    missing_specialties: list[str]
    distinct_reviewers: int
    is_complete: bool


class BCDFeedbackCreate(BaseModel):
    section_key: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)


class BCDFeedbackResponse(BaseModel):
    id: str
    bcd_id: str
    section_key: str
    author_id: str
    content: str
    resolved: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BCDListResponse(BaseModel):
    id: str
    book_id: str
    section_label: str | None
    version: int
    is_active: bool
    status: BCDStatus
    prepared_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BCDResponse(BCDListResponse):
    section_range_start: int | None
    section_range_end: int | None
    structural_outline: dict | None
    participant_register: list | None
    discourse_threads: list | None
    theological_spine: str | None
    places: list | None
    objects: list | None
    institutions: list | None
    genre_context: dict | None
    maintenance_notes: dict | None
    generation_metadata: dict | None


class EstablishedItem(BaseModel):
    category: str
    name: str
    english_gloss: str = ""
    description: str
    verse_reference: str


class PassageEntryBriefResponse(BaseModel):
    participants: list[dict]
    active_threads: list[dict]
    places: list[dict]
    objects: list[dict]
    institutions: list[dict]
    established_items: list[EstablishedItem]
    is_first_pericope: bool
    bcd_version: int


class BCDGenerationLogResponse(BaseModel):
    id: str
    bcd_id: str
    step_name: str
    step_order: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    input_summary: str | None
    output_summary: str | None
    token_count: int | None
    error_detail: str | None

    model_config = {"from_attributes": True}
