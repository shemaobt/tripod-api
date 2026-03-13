import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.db.models.oc_recording import OC_Recording
from app.services.oral_collector.constants import GCS_OC_BUCKET, GCS_OC_PROJECT
from app.services.oral_collector.gcs_utils import upload_gcs_blob
from app.services.oral_collector.require_manager import require_project_manager

logger = logging.getLogger(__name__)


async def _get_recording(db: AsyncSession, recording_id: str) -> OC_Recording:

    stmt = select(OC_Recording).where(OC_Recording.id == recording_id)
    result = await db.execute(stmt)
    recording = result.scalar_one_or_none()
    if not recording:
        raise NotFoundError("Recording not found")
    return recording


async def _copy_gcs_blob(source_name: str, dest_name: str) -> None:

    from google.cloud import storage

    client = storage.Client(project=GCS_OC_PROJECT)
    bucket = client.bucket(GCS_OC_BUCKET)
    source_blob = bucket.blob(source_name)
    bucket.copy_blob(source_blob, bucket, dest_name)


def _blob_name_from_url(gcs_url: str) -> str | None:

    prefix = f"https://storage.googleapis.com/{GCS_OC_BUCKET}/"
    if not gcs_url.startswith(prefix):
        return None
    return gcs_url[len(prefix) :]


def _original_blob_name(blob_name: str) -> str:

    dot_idx = blob_name.rfind(".")
    if dot_idx == -1:
        return f"{blob_name}_original"
    return f"{blob_name[:dot_idx]}_original{blob_name[dot_idx:]}"


async def trigger_cleaning(db: AsyncSession, recording_id: str, user_id: str) -> OC_Recording:

    recording = await _get_recording(db, recording_id)
    await require_project_manager(
        db, recording.project_id, user_id, action="trigger audio cleaning"
    )

    if not recording.gcs_url:
        raise NotFoundError("Recording has no uploaded audio file")

    recording.cleaning_status = "cleaning"
    await db.commit()
    await db.refresh(recording)

    settings = get_settings()

    try:
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

        cleaned_url = result.get("output_url", "")

        async with httpx.AsyncClient() as client:
            cleaned_resp = await client.get(cleaned_url, timeout=120.0)
            cleaned_resp.raise_for_status()
            cleaned_data = cleaned_resp.content

        blob_name = _blob_name_from_url(recording.gcs_url)
        if blob_name:
            original_name = _original_blob_name(blob_name)
            await _copy_gcs_blob(blob_name, original_name)

            await upload_gcs_blob(blob_name, cleaned_data, "application/octet-stream")

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

    return await _get_recording(db, recording_id)
