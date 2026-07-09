import gzip
import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AcoustemeStatus
from app.core.exceptions import NotFoundError, ValidationError
from app.db.models.oc_acousteme import OC_AcoustemeArtifact
from app.models.oc_acousteme import AcoustemeStreamResponse
from app.services.oral_collector.constants import GCS_OC_BUCKET
from app.services.oral_collector.gcs_utils import (
    generate_signed_download_url,
    upload_gcs_object,
)

logger = logging.getLogger(__name__)

# The acousteme grid is fixed by the tokenizer: 20 ms hop, 100-unit codebook.
# These are uniform across every recording — do not vary them per audio.
ACOUSTEME_HOP_SEC = 0.02
ACOUSTEME_NUM_UNITS = 100

# Chunk-size presets (in frames) the frontend groups acoustemes by, mirroring the
# beads viewer's Small/Medium/Large. The smallest respects the 20 ms supervision
# grid; sizes are whole frames so chunk boundaries land on frame edges.
ACOUSTEME_GRANULARITY_FRAMES: dict[str, int] = {"small": 10, "medium": 25, "large": 50}

DOWNLOAD_URL_EXPIRY_MINUTES = 15


def acousteme_blob_path(recording_id: str, codebook_version: str) -> str:
    return f"acoustemes/{recording_id}/{codebook_version}.json.gz"


async def _authorize(db: AsyncSession, recording_id: str, user_id: str) -> None:
    # Local import: recording_service participates in a module-load cycle with
    # app.inngest, so it must not be imported at module top here.
    from app.services.oral_collector import recording_service

    recording = await recording_service.get_recording(db, recording_id)
    await recording_service.check_recording_access(db, recording, user_id)


async def get_artifact(
    db: AsyncSession,
    recording_id: str,
    user_id: str,
    *,
    codebook_version: str | None = None,
) -> OC_AcoustemeArtifact:
    """Fetch one artifact pointer, defaulting to the newest version."""

    await _authorize(db, recording_id, user_id)

    stmt = select(OC_AcoustemeArtifact).where(OC_AcoustemeArtifact.recording_id == recording_id)
    if codebook_version is not None:
        stmt = stmt.where(OC_AcoustemeArtifact.codebook_version == codebook_version)
    stmt = stmt.order_by(OC_AcoustemeArtifact.created_at.desc())

    artifact = (await db.execute(stmt)).scalars().first()
    if artifact is None:
        raise NotFoundError(f"No acousteme artifact for recording {recording_id}")
    return artifact


async def list_artifacts(
    db: AsyncSession, recording_id: str, user_id: str
) -> list[OC_AcoustemeArtifact]:
    """List every codebook version available for a recording, newest first."""

    await _authorize(db, recording_id, user_id)
    stmt = (
        select(OC_AcoustemeArtifact)
        .where(OC_AcoustemeArtifact.recording_id == recording_id)
        .order_by(OC_AcoustemeArtifact.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_stream(
    db: AsyncSession,
    recording_id: str,
    user_id: str,
    *,
    codebook_version: str | None = None,
) -> AcoustemeStreamResponse:
    """Return a signed download URL + grid metadata for the frontend."""

    artifact = await get_artifact(db, recording_id, user_id, codebook_version=codebook_version)
    if artifact.status != AcoustemeStatus.READY:
        raise ValidationError(
            f"Acousteme artifact for recording {recording_id} is not ready "
            f"(status: {artifact.status})"
        )

    download_url = await generate_signed_download_url(
        artifact.gcs_bucket,
        artifact.gcs_object,
        expiry_minutes=DOWNLOAD_URL_EXPIRY_MINUTES,
        response_content_type="application/json",
    )
    expires_at = datetime.now(UTC) + timedelta(minutes=DOWNLOAD_URL_EXPIRY_MINUTES)

    return AcoustemeStreamResponse(
        recording_id=artifact.recording_id,
        codebook_version=artifact.codebook_version,
        download_url=download_url,
        expires_at=expires_at,
        content_encoding=artifact.content_encoding,
        duration_sec=artifact.duration_sec,
        num_frames=artifact.num_frames,
        hop_sec=artifact.hop_sec,
        num_units=artifact.num_units,
        granularity_frames=ACOUSTEME_GRANULARITY_FRAMES,
    )


async def store_artifact(
    db: AsyncSession,
    *,
    recording_id: str,
    codebook_version: str,
    stream: dict[str, Any],
    bucket: str = GCS_OC_BUCKET,
) -> OC_AcoustemeArtifact:
    """Persist a tokenizer-produced stream: gzip → upload → upsert pointer row.

    ``stream`` is the tokenizer output, at minimum ``duration_sec``,
    ``num_frames`` and ``segments`` ([{start, end, unit_id}, ...]). The
    redundant per-frame ``timestamps`` array is dropped if present — it is
    derivable from hop_sec and num_frames. Called by the ingestion pipeline, not
    by request handlers.
    """

    segments = stream.get("segments") or []
    payload = {
        "recording_id": recording_id,
        "codebook_version": codebook_version,
        "hop_sec": ACOUSTEME_HOP_SEC,
        "num_units": ACOUSTEME_NUM_UNITS,
        "duration_sec": stream.get("duration_sec"),
        "num_frames": stream.get("num_frames"),
        "segments": segments,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    gz = gzip.compress(raw)
    sha256 = hashlib.sha256(gz).hexdigest()

    blob_name = acousteme_blob_path(recording_id, codebook_version)
    await upload_gcs_object(bucket, blob_name, gz, "application/json", content_encoding="gzip")

    artifact = await db.get(
        OC_AcoustemeArtifact,
        {"recording_id": recording_id, "codebook_version": codebook_version},
    )
    if artifact is None:
        artifact = OC_AcoustemeArtifact(
            recording_id=recording_id, codebook_version=codebook_version
        )
        db.add(artifact)

    artifact.status = AcoustemeStatus.READY
    artifact.gcs_bucket = bucket
    artifact.gcs_object = blob_name
    artifact.content_encoding = "gzip"
    artifact.duration_sec = stream.get("duration_sec")
    artifact.num_frames = stream.get("num_frames")
    artifact.hop_sec = ACOUSTEME_HOP_SEC
    artifact.num_segments = len(segments)
    artifact.num_units = ACOUSTEME_NUM_UNITS
    artifact.distinct_units = len({s["unit_id"] for s in segments})
    artifact.size_bytes = len(gz)
    artifact.sha256 = sha256
    artifact.error = None

    await db.commit()
    await db.refresh(artifact)
    return artifact
