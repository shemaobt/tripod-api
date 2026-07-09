from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.enums import AcoustemeStatus


class OC_AcoustemeArtifact(Base):
    """Pointer to one recording's acousteme stream.

    The stream itself (the frame-level ``segments`` produced by the acoustic
    tokenizer) is an immutable, write-once blob living in GCS; this row is the
    queryable pointer + grid metadata the backend serves so the frontend can
    fetch it by ``recording_id`` and chunk it client-side. One row per
    (recording, codebook_version): a codebook change is a new version, never an
    in-place edit.
    """

    __tablename__ = "oc_acousteme_artifacts"

    recording_id: Mapped[str] = mapped_column(
        ForeignKey("oc_recordings.id", ondelete="CASCADE"), primary_key=True
    )
    # Frozen K-means codebook the unit ids are meaningless without. Part of the
    # key so re-clustering yields a new artifact rather than silently corrupting
    # every stored reference.
    codebook_version: Mapped[str] = mapped_column(String(64), primary_key=True)

    status: Mapped[str] = mapped_column(String(20), default=AcoustemeStatus.PENDING, index=True)

    # GCS location of the gzipped JSON stream. Bucket is stored per row so pilot
    # buckets (e.g. terena-pilot) and the shared bucket can coexist.
    gcs_bucket: Mapped[str] = mapped_column(String(255))
    gcs_object: Mapped[str] = mapped_column(Text)
    content_encoding: Mapped[str] = mapped_column(String(20), default="gzip")

    # Grid metadata — enough for the frontend to lay out chunks without opening
    # the blob. hop_sec * frame_index = time; num_units is the codebook size.
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    num_frames: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hop_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    num_segments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distinct_units: Mapped[int | None] = mapped_column(Integer, nullable=True)

    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
