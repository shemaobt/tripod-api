from pydantic import BaseModel


class UploadConfirmedPayload(BaseModel):
    recording_id: str
    user_id: str | None = None
    expected_blob_path: str
    expected_size_bytes: int
    expected_md5_hash: str | None = None


class CleanRequestedPayload(BaseModel):
    recording_id: str
    user_id: str
    gcs_url: str


class SplitSegmentData(BaseModel):
    start_seconds: float
    end_seconds: float
    genre_id: str
    subcategory_id: str
    register_id: str | None = None
    gain_db: float | None = None


class SplitRequestedPayload(BaseModel):
    recording_id: str
    user_id: str
    segments: list[SplitSegmentData]
    project_id: str
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
