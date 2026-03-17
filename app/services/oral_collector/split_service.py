import asyncio
import logging
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import inngest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CleaningStatus, OCRecordingEvent, SplittingStatus, UploadStatus
from app.core.exceptions import NotFoundError, ValidationError
from app.core.inngest_client import inngest_client
from app.db.models.oc_recording import OC_Recording
from app.inngest.schemas import SplitRequestedPayload, SplitSegmentData
from app.models.oc_recording import SplitSegment
from app.services.oral_collector.gcs_utils import upload_gcs_blob
from app.services.oral_collector.recording_service import (
    FORMAT_EXTENSIONS,
    _gcs_blob_path,
    check_recording_access,
    get_recording,
)

logger = logging.getLogger(__name__)


async def _download_audio(gcs_url: str) -> bytes:

    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(gcs_url, timeout=120.0)
        resp.raise_for_status()
        return resp.content


async def _ffmpeg_split_segment(
    input_path: Path, output_path: Path, start: float, end: float
) -> None:

    duration = end - start
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-c",
        "copy",
        str(output_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")


def _content_type_for_format(fmt: str) -> str:

    mapping = {
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "webm": "audio/webm",
    }
    return mapping.get(fmt.lower(), "application/octet-stream")


async def request_split(
    db: AsyncSession,
    recording_id: str,
    segments: list[SplitSegment],
    user_id: str,
) -> OC_Recording:
    recording = await get_recording(db, recording_id)
    await check_recording_access(db, recording, user_id)

    if not recording.gcs_url:
        raise NotFoundError("Recording has no uploaded audio file")

    if recording.upload_status != UploadStatus.VERIFIED:
        raise ValidationError(
            "Recording must be verified before splitting. "
            f"Current status: {recording.upload_status}"
        )

    recording.splitting_status = SplittingStatus.SPLITTING
    await db.commit()
    await db.refresh(recording)

    payload = SplitRequestedPayload(
        recording_id=recording_id,
        user_id=user_id,
        segments=[
            SplitSegmentData(start_seconds=s.start_seconds, end_seconds=s.end_seconds)
            for s in segments
        ],
        project_id=recording.project_id,
        genre_id=recording.genre_id,
        subcategory_id=recording.subcategory_id,
        format=recording.format,
        title=recording.title or "Recording",
        recorded_at=recording.recorded_at.isoformat(),
    )
    await inngest_client.send(
        inngest.Event(name=OCRecordingEvent.SPLIT_REQUESTED, data=payload.model_dump())
    )

    return recording


async def get_split_status(db: AsyncSession, recording_id: str) -> tuple[OC_Recording, list[str]]:
    recording = await get_recording(db, recording_id)

    segment_ids: list[str] = []
    if recording.splitting_status == SplittingStatus.COMPLETED:
        stmt = (
            select(OC_Recording.id)
            .where(OC_Recording.split_from_id == recording_id)
            .order_by(OC_Recording.created_at)
        )
        result = await db.execute(stmt)
        segment_ids = list(result.scalars().all())

    return recording, segment_ids


async def split_recording(
    db: AsyncSession,
    recording_id: str,
    segments: list[SplitSegment],
    user_id: str,
) -> list[str]:
    recording = await get_recording(db, recording_id)
    await check_recording_access(db, recording, user_id)

    if not recording.gcs_url:
        raise NotFoundError("Recording has no uploaded audio file")

    audio_data = await _download_audio(recording.gcs_url)
    fmt = recording.format.lower()
    ext = FORMAT_EXTENSIONS.get(fmt, f".{fmt}")

    new_ids: list[str] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        input_file = tmp / f"original{ext}"
        input_file.write_bytes(audio_data)

        for i, seg in enumerate(segments):
            new_id = str(uuid.uuid4())
            output_file = tmp / f"segment_{i}{ext}"

            await _ffmpeg_split_segment(input_file, output_file, seg.start_seconds, seg.end_seconds)

            segment_bytes = output_file.read_bytes()
            blob_path = _gcs_blob_path(recording.project_id, recording.genre_id, new_id, fmt)
            content_type = _content_type_for_format(fmt)
            gcs_url = await upload_gcs_blob(blob_path, segment_bytes, content_type)

            duration = seg.end_seconds - seg.start_seconds
            new_recording = OC_Recording(
                id=new_id,
                project_id=recording.project_id,
                genre_id=recording.genre_id,
                subcategory_id=recording.subcategory_id,
                user_id=recording.user_id,
                title=f"{recording.title or 'Recording'} (segment {i + 1})",
                duration_seconds=duration,
                file_size_bytes=len(segment_bytes),
                format=recording.format,
                gcs_url=gcs_url,
                upload_status=UploadStatus.VERIFIED,
                cleaning_status=CleaningStatus.NONE,
                splitting_status=SplittingStatus.NONE,
                split_from_id=recording_id,
                recorded_at=recording.recorded_at,
                uploaded_at=datetime.now(UTC),
            )
            db.add(new_recording)
            new_ids.append(new_id)

        await db.commit()

    logger.info(
        "Split recording %s into %d segments: %s",
        recording_id,
        len(new_ids),
        new_ids,
    )
    return new_ids
