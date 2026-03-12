from datetime import datetime

from pydantic import BaseModel, Field


class RecordingCreate(BaseModel):
    project_id: str
    genre_id: str
    subcategory_id: str
    title: str | None = Field(default=None, max_length=500)
    duration_seconds: float = Field(ge=0)
    file_size_bytes: int = Field(ge=0)
    format: str = Field(min_length=1, max_length=20)
    recorded_at: datetime


class RecordingUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    genre_id: str | None = None
    subcategory_id: str | None = None


class RecordingResponse(BaseModel):
    id: str
    project_id: str
    genre_id: str
    subcategory_id: str
    user_id: str
    title: str | None
    duration_seconds: float
    file_size_bytes: int
    format: str
    gcs_url: str | None
    upload_status: str
    cleaning_status: str
    recorded_at: datetime
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CleaningStatusResponse(BaseModel):
    recording_id: str
    cleaning_status: str

    model_config = {"from_attributes": True}


class UploadUrlRequest(BaseModel):
    recording_id: str
    format: str = Field(min_length=1, max_length=20)


class UploadUrlResponse(BaseModel):
    recording_id: str
    server_id: str
    upload_url: str
    expires_at: datetime


class SplitSegment(BaseModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)


class SplitRequest(BaseModel):
    segments: list[SplitSegment] = Field(min_length=1)


class SplitResponse(BaseModel):
    recording_ids: list[str]
