import logging
from datetime import UTC, datetime, timedelta

import inngest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ACTIVE_UPLOAD_STATUSES, OCRecordingEvent, UploadStatus
from app.core.exceptions import AuthorizationError, NotFoundError
from app.core.inngest_client import inngest_client
from app.db.models.oc_recording import OC_Recording
from app.db.models.project import ProjectUserAccess
from app.inngest.schemas import UploadConfirmedPayload
from app.models.oc_recording import RecordingCreate, RecordingUpdate, UploadUrlResponse
from app.services.oral_collector.constants import GCS_OC_BUCKET, GCS_OC_PROJECT
from app.services.oral_collector.gcs_utils import GCS_PUBLIC_BASE

logger = logging.getLogger(__name__)

FORMAT_EXTENSIONS: dict[str, str] = {
    "m4a": ".m4a",
    "aac": ".aac",
    "mp3": ".mp3",
    "wav": ".wav",
    "ogg": ".ogg",
    "webm": ".webm",
}

SIGNED_URL_EXPIRY_MINUTES = 15


async def list_recordings(
    db: AsyncSession,
    project_id: str,
    *,
    genre_id: str | None = None,
    subcategory_id: str | None = None,
    upload_status: str | None = None,
    cleaning_status: str | None = None,
    user_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[OC_Recording]:

    stmt = (
        select(OC_Recording)
        .where(OC_Recording.project_id == project_id)
        .order_by(OC_Recording.recorded_at.desc())
    )
    if genre_id:
        stmt = stmt.where(OC_Recording.genre_id == genre_id)
    if subcategory_id:
        stmt = stmt.where(OC_Recording.subcategory_id == subcategory_id)
    if upload_status:
        stmt = stmt.where(OC_Recording.upload_status == upload_status)
    else:
        stmt = stmt.where(OC_Recording.upload_status.in_(ACTIVE_UPLOAD_STATUSES))
    if cleaning_status:
        stmt = stmt.where(OC_Recording.cleaning_status == cleaning_status)
    if user_id:
        stmt = stmt.where(OC_Recording.user_id == user_id)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_recording(db: AsyncSession, recording_id: str) -> OC_Recording:

    stmt = select(OC_Recording).where(OC_Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    if not recording:
        raise NotFoundError("Recording not found")
    return recording


async def check_recording_access(db: AsyncSession, recording: OC_Recording, user_id: str) -> None:

    if recording.user_id == user_id:
        return
    stmt = select(ProjectUserAccess).where(
        ProjectUserAccess.project_id == recording.project_id,
        ProjectUserAccess.user_id == user_id,
        ProjectUserAccess.role == "manager",
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise AuthorizationError(
            "Only the recording owner or a project manager can modify this recording"
        )


async def create_recording(db: AsyncSession, data: RecordingCreate, user_id: str) -> OC_Recording:

    recording = OC_Recording(
        project_id=data.project_id,
        genre_id=data.genre_id,
        subcategory_id=data.subcategory_id,
        register_id=data.register_id,
        user_id=user_id,
        title=data.title,
        duration_seconds=data.duration_seconds,
        file_size_bytes=data.file_size_bytes,
        format=data.format,
        recorded_at=data.recorded_at,
    )
    db.add(recording)
    await db.commit()
    await db.refresh(recording)
    return recording


async def update_recording(
    db: AsyncSession, recording_id: str, data: RecordingUpdate
) -> OC_Recording:

    recording = await get_recording(db, recording_id)
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(recording, field, value)
    await db.commit()
    await db.refresh(recording)
    return recording


async def delete_recording(db: AsyncSession, recording_id: str) -> None:

    recording = await get_recording(db, recording_id)
    if recording.upload_status in ACTIVE_UPLOAD_STATUSES and recording.gcs_url:
        _delete_gcs_blob(recording.gcs_url)
    await db.delete(recording)
    await db.commit()


def _gcs_blob_path(project_id: str, genre_id: str, recording_id: str, fmt: str) -> str:

    ext = FORMAT_EXTENSIONS.get(fmt.lower(), f".{fmt.lower()}")
    return f"oral-collector/{project_id}/{genre_id}/{recording_id}{ext}"


async def generate_upload_url(
    db: AsyncSession,
    recording_id: str,
    fmt: str,
    user_id: str,
) -> UploadUrlResponse:

    from google.cloud import storage

    recording = await get_recording(db, recording_id)
    await check_recording_access(db, recording, user_id)

    blob_path = _gcs_blob_path(recording.project_id, recording.genre_id, recording_id, fmt)

    client = storage.Client(project=GCS_OC_PROJECT)
    bucket = client.bucket(GCS_OC_BUCKET)
    blob = bucket.blob(blob_path)

    expiry = timedelta(minutes=SIGNED_URL_EXPIRY_MINUTES)
    upload_url = blob.generate_signed_url(
        version="v4",
        expiration=expiry,
        method="PUT",
        content_type="audio/mp4",
    )

    expires_at = datetime.now(UTC) + expiry

    recording.upload_status = UploadStatus.UPLOADING
    await db.commit()

    return UploadUrlResponse(
        recording_id=recording_id,
        server_id=recording_id,
        upload_url=upload_url,
        expires_at=expires_at,
    )


async def confirm_upload(db: AsyncSession, recording_id: str) -> OC_Recording:
    recording = await get_recording(db, recording_id)

    blob_path = _gcs_blob_path(
        recording.project_id,
        recording.genre_id,
        recording_id,
        recording.format,
    )

    payload = UploadConfirmedPayload(
        recording_id=recording_id,
        user_id=recording.user_id,
        expected_blob_path=blob_path,
        expected_size_bytes=recording.file_size_bytes,
    )
    await inngest_client.send(
        inngest.Event(name=OCRecordingEvent.UPLOAD_CONFIRMED, data=payload.model_dump())
    )

    return recording


def _delete_gcs_blob(gcs_url: str) -> None:

    try:
        from google.cloud import storage

        if not gcs_url.startswith(GCS_PUBLIC_BASE):
            logger.warning("Unexpected GCS URL format: %s", gcs_url)
            return
        blob_name = gcs_url[len(GCS_PUBLIC_BASE) :]
        client = storage.Client(project=GCS_OC_PROJECT)
        bucket = client.bucket(GCS_OC_BUCKET)
        blob = bucket.blob(blob_name)
        blob.delete()
    except Exception:
        logger.exception("Failed to delete GCS blob: %s", gcs_url)
