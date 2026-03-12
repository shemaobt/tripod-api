import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.models.oc_recording import OC_Recording
from app.db.models.project import ProjectUserAccess

logger = logging.getLogger(__name__)

GCS_OC_BUCKET = "tripod-image-uploads"
GCS_OC_PROJECT = "gen-lang-client-0886209230"


async def _require_manager(db: AsyncSession, project_id: str, user_id: str) -> None:
    """Verify the user is a manager for the given project."""
    stmt = select(ProjectUserAccess).where(
        ProjectUserAccess.project_id == project_id,
        ProjectUserAccess.user_id == user_id,
        ProjectUserAccess.role == "manager",
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise AuthorizationError("Only project managers can trigger audio cleaning")


async def _get_recording(db: AsyncSession, recording_id: str) -> OC_Recording:
    """Return a single recording by ID or raise NotFoundError."""
    stmt = select(OC_Recording).where(OC_Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    if not recording:
        raise NotFoundError("Recording not found")
    return recording


async def _copy_gcs_blob(source_name: str, dest_name: str) -> None:
    """Copy a GCS blob from source_name to dest_name within the OC bucket."""
    from google.cloud import storage  # type: ignore[import-untyped]

    client = storage.Client(project=GCS_OC_PROJECT)
    bucket = client.bucket(GCS_OC_BUCKET)
    source_blob = bucket.blob(source_name)
    bucket.copy_blob(source_blob, bucket, dest_name)


async def _upload_gcs_blob(blob_name: str, data: bytes, content_type: str) -> None:
    """Upload bytes to a GCS blob in the OC bucket."""
    from google.cloud import storage  # type: ignore[import-untyped]

    client = storage.Client(project=GCS_OC_PROJECT)
    bucket = client.bucket(GCS_OC_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data, content_type=content_type)


def _blob_name_from_url(gcs_url: str) -> str | None:
    """Extract the blob name from a GCS public URL."""
    prefix = f"https://storage.googleapis.com/{GCS_OC_BUCKET}/"
    if not gcs_url.startswith(prefix):
        return None
    return gcs_url[len(prefix) :]


def _original_blob_name(blob_name: str) -> str:
    """Return the blob name with '_original' inserted before the extension."""
    dot_idx = blob_name.rfind(".")
    if dot_idx == -1:
        return f"{blob_name}_original"
    return f"{blob_name[:dot_idx]}_original{blob_name[dot_idx:]}"


async def trigger_cleaning(db: AsyncSession, recording_id: str, user_id: str) -> OC_Recording:
    """Trigger audio cleaning for a recording via third-party API.

    1. Verify the user is a project manager for the recording's project.
    2. Send the recording's GCS URL to the cleaning API.
    3. On success: save original with _original suffix, replace primary with cleaned version.
    4. On failure: set cleaning_status to 'failed'.
    """
    recording = await _get_recording(db, recording_id)
    await _require_manager(db, recording.project_id, user_id)

    if not recording.gcs_url:
        raise NotFoundError("Recording has no uploaded audio file")

    # Set status to 'cleaning' while processing
    recording.cleaning_status = "cleaning"
    await db.commit()
    await db.refresh(recording)

    settings = get_settings()

    try:
        # Send GCS URL to third-party cleaning API
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                settings.cleaning_api_url,
                json={"input_url": recording.gcs_url},
                headers={
                    "Authorization": f"Bearer {settings.cleaning_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
            resp.raise_for_status()
            result = resp.json()

        # Extract cleaned audio from response
        cleaned_url = result.get("output_url", "")

        # Download the cleaned audio
        async with httpx.AsyncClient() as client:
            cleaned_resp = await client.get(cleaned_url, timeout=120.0)
            cleaned_resp.raise_for_status()
            cleaned_data = cleaned_resp.content

        # Save original file with _original suffix in GCS
        blob_name = _blob_name_from_url(recording.gcs_url)
        if blob_name:
            original_name = _original_blob_name(blob_name)
            await _copy_gcs_blob(blob_name, original_name)

            # Upload cleaned version to replace primary
            await _upload_gcs_blob(blob_name, cleaned_data, "application/octet-stream")

        recording.cleaning_status = "cleaned"
        await db.commit()
        await db.refresh(recording)

    except Exception:
        logger.exception("Audio cleaning failed for recording %s", recording_id)
        recording.cleaning_status = "failed"
        await db.commit()
        await db.refresh(recording)

    return recording


async def get_cleaning_status(db: AsyncSession, recording_id: str) -> OC_Recording:
    """Return the current cleaning status of a recording."""
    return await _get_recording(db, recording_id)
