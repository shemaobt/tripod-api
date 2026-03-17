import logging

import httpx
import inngest

from app.core.config import get_settings
from app.core.enums import (
    CleaningStatus,
    OCNotificationEvent,
    OCRecordingEvent,
)
from app.core.inngest_client import inngest_client
from app.inngest.helpers import (
    check_recording_verified,
    extract_failure_context,
    notify_user,
    update_recording_fields,
)
from app.inngest.schemas import CleanRequestedPayload
from app.services.oral_collector.gcs_utils import (
    blob_name_from_url,
    copy_gcs_blob,
    original_blob_name,
    upload_gcs_blob,
)

logger = logging.getLogger(__name__)


async def _on_clean_failure(ctx: inngest.Context, _step: inngest.Step) -> None:
    fc = extract_failure_context(ctx, "Cleaning failed")

    await update_recording_fields(
        fc.recording_id,
        cleaning_status=CleaningStatus.FAILED,
        cleaning_error=fc.error_message,
    )

    if fc.user_id:
        await notify_user(
            fc.user_id,
            OCNotificationEvent.CLEANING_FAILED,
            "Audio cleaning failed",
            f"Audio cleaning failed: {fc.error_message}",
        )


@inngest_client.create_function(
    fn_id="clean-recording",
    trigger=inngest.TriggerEvent(event=OCRecordingEvent.CLEAN_REQUESTED),
    retries=3,
    on_failure=_on_clean_failure,  # type: ignore[arg-type]
)
async def clean_recording_fn(ctx: inngest.Context, step: inngest.Step) -> str:
    payload = CleanRequestedPayload.model_validate(ctx.event.data)

    verified_url = await step.run(
        "check-verified",
        lambda: check_recording_verified(payload.recording_id),
    )

    async def _call_cleaning_api() -> str:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                settings.cleaning_api_url,
                json={"input_url": verified_url or payload.gcs_url},
                headers={
                    "Authorization": f"Bearer {settings.cleaning_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            )
            resp.raise_for_status()
            result = resp.json()
        return str(result.get("output_url", ""))

    cleaned_url = await step.run("call-cleaning-api", _call_cleaning_api)

    async def _download_cleaned() -> bytes:
        async with httpx.AsyncClient() as client:
            resp = await client.get(cleaned_url, timeout=120.0)
            resp.raise_for_status()
            return resp.content

    cleaned_data = await step.run("download-cleaned-audio", _download_cleaned)

    async def _backup_and_upload() -> None:
        blob_name = blob_name_from_url(verified_url or payload.gcs_url)
        if blob_name:
            backup_name = original_blob_name(blob_name)
            await copy_gcs_blob(blob_name, backup_name)
            await upload_gcs_blob(blob_name, cleaned_data, "application/octet-stream")

    await step.run("backup-and-upload", _backup_and_upload)

    async def _update_status() -> None:
        await update_recording_fields(
            payload.recording_id,
            cleaning_status=CleaningStatus.CLEANED,
            cleaning_error=None,
        )
        await notify_user(
            payload.user_id,
            OCNotificationEvent.CLEANING_COMPLETED,
            "Audio cleaning complete",
            "Your recording has been cleaned successfully.",
        )

    await step.run("update-status", _update_status)

    return CleaningStatus.CLEANED
