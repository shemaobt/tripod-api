from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.core.enums import CleaningStatus, SplittingStatus

_SECONDARY_TRIPLE_ERROR = (
    "secondary classification must differ from the primary in at least one of "
    "register, genre, or subcategory"
)


def secondary_equals_primary(
    *,
    primary_register_id: str | None,
    primary_genre_id: str | None,
    primary_subcategory_id: str | None,
    secondary_register_id: str | None,
    secondary_genre_id: str | None,
    secondary_subcategory_id: str | None,
) -> bool:
    # Returns True only when the full (register, genre, subcategory) triple of
    # the secondary is identical to the primary AND any secondary field is set.
    # (Fully-null secondary never counts as identical.)
    if (
        secondary_register_id is None
        and secondary_genre_id is None
        and secondary_subcategory_id is None
    ):
        return False
    return (
        primary_register_id == secondary_register_id
        and primary_genre_id == secondary_genre_id
        and primary_subcategory_id == secondary_subcategory_id
    )


class RecordingCreate(BaseModel):
    project_id: str
    genre_id: str
    subcategory_id: str
    register_id: str | None = None
    secondary_genre_id: str | None = None
    secondary_subcategory_id: str | None = None
    secondary_register_id: str | None = None
    storyteller_id: str | None = None
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    duration_seconds: float = Field(ge=0)
    file_size_bytes: int = Field(ge=0)
    format: str = Field(min_length=1, max_length=20)
    recorded_at: datetime

    @model_validator(mode="after")
    def _check_secondary_triple_not_identical(self) -> "RecordingCreate":
        if secondary_equals_primary(
            primary_register_id=self.register_id,
            primary_genre_id=self.genre_id,
            primary_subcategory_id=self.subcategory_id,
            secondary_register_id=self.secondary_register_id,
            secondary_genre_id=self.secondary_genre_id,
            secondary_subcategory_id=self.secondary_subcategory_id,
        ):
            raise ValueError(_SECONDARY_TRIPLE_ERROR)
        return self


class RecordingUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    genre_id: str | None = None
    subcategory_id: str | None = None
    register_id: str | None = None
    secondary_genre_id: str | None = None
    secondary_subcategory_id: str | None = None
    secondary_register_id: str | None = None
    storyteller_id: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    file_size_bytes: int | None = Field(default=None, ge=0)
    cleaning_status: CleaningStatus | None = None

    @model_validator(mode="after")
    def _check_secondary_triple_not_identical(self) -> "RecordingUpdate":
        # Patch-only check: catches the case where the request itself contains
        # all six fields and they form an identical triple. The service layer
        # does the comprehensive merge with the existing recording.
        if secondary_equals_primary(
            primary_register_id=self.register_id,
            primary_genre_id=self.genre_id,
            primary_subcategory_id=self.subcategory_id,
            secondary_register_id=self.secondary_register_id,
            secondary_genre_id=self.secondary_genre_id,
            secondary_subcategory_id=self.secondary_subcategory_id,
        ):
            raise ValueError(_SECONDARY_TRIPLE_ERROR)
        return self


class RecordingResponse(BaseModel):
    id: str
    project_id: str
    genre_id: str
    subcategory_id: str
    register_id: str | None = None
    secondary_genre_id: str | None = None
    secondary_subcategory_id: str | None = None
    secondary_register_id: str | None = None
    storyteller_id: str | None = None
    user_id: str | None = None
    title: str | None
    description: str | None = None
    duration_seconds: float
    file_size_bytes: int
    format: str
    gcs_url: str | None
    upload_status: str
    upload_error: str | None = None
    cleaning_status: str
    cleaning_error: str | None = None
    splitting_status: str = SplittingStatus.NONE
    split_from_id: str | None = None
    split_index: int | None = None
    split_segment_count: int | None = None
    recorded_at: datetime
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CleaningStatusResponse(BaseModel):
    recording_id: str
    cleaning_status: str
    cleaning_error: str | None = None

    model_config = {"from_attributes": True}


class SplitStatusResponse(BaseModel):
    recording_id: str
    splitting_status: str
    segment_ids: list[str] = []


class UploadUrlRequest(BaseModel):
    recording_id: str
    format: str = Field(min_length=1, max_length=20)


class UploadUrlResponse(BaseModel):
    recording_id: str
    server_id: str
    upload_url: str
    expires_at: datetime
    content_type: str


class ResumableUploadUrlRequest(BaseModel):
    recording_id: str
    format: str = Field(min_length=1, max_length=20)


class ResumableUploadUrlResponse(BaseModel):
    recording_id: str
    session_uri: str
    chunk_size_bytes: int
    content_type: str


class ConfirmUploadRequest(BaseModel):
    md5_hash: str | None = None
    crc32c: str | None = None


class SplitSegment(BaseModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    genre_id: str | None = None
    subcategory_id: str | None = None
    register_id: str | None = None
    gain_db: float | None = None


class SplitRequest(BaseModel):
    segments: list[SplitSegment] = Field(min_length=1)
