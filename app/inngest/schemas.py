from pydantic import BaseModel


class UploadConfirmedPayload(BaseModel):
    recording_id: str
    user_id: str
    expected_blob_path: str
    expected_size_bytes: int


class CleanRequestedPayload(BaseModel):
    recording_id: str
    user_id: str
    gcs_url: str


class SplitSegmentData(BaseModel):
    start_seconds: float
    end_seconds: float


class SplitRequestedPayload(BaseModel):
    recording_id: str
    user_id: str
    segments: list[SplitSegmentData]
    project_id: str
    genre_id: str
    subcategory_id: str
    format: str
    title: str
    recorded_at: str


class BlobVerificationResult(BaseModel):
    size: int


class SegmentResult(BaseModel):
    id: str
    gcs_url: str
    duration_seconds: float
    file_size_bytes: int
    index: int
