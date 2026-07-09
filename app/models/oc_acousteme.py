from datetime import datetime

from pydantic import BaseModel


class AcoustemeArtifactResponse(BaseModel):
    """Queryable metadata for one recording's acousteme stream (no payload)."""

    recording_id: str
    codebook_version: str
    status: str
    duration_sec: float | None = None
    num_frames: int | None = None
    hop_sec: float | None = None
    num_segments: int | None = None
    num_units: int | None = None
    distinct_units: int | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AcoustemeStreamResponse(BaseModel):
    """Everything the frontend needs to load + chunk one stream.

    ``download_url`` is a short-lived signed GET URL for the gzipped JSON blob;
    the grid fields let the client lay out Small/Medium/Large chunks before the
    blob arrives. Chunk indices are a client-side view — never persisted.
    """

    recording_id: str
    codebook_version: str
    download_url: str
    expires_at: datetime
    content_encoding: str
    duration_sec: float | None = None
    num_frames: int | None = None
    hop_sec: float | None = None
    num_units: int | None = None
    granularity_frames: dict[str, int]
