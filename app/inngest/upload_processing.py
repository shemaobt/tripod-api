import logging
from datetime import UTC, datetime

import inngest

from app.core.database import AsyncSessionLocal
from app.core.enums import (
    OCNotificationEvent,
    OCRecordingEvent,
    UploadStatus,
)
from app.core.inngest_client import inngest_client
from app.db.models.oc_recording import OC_Recording
from app.inngest.helpers import (
    extract_failure_context,
    notify_user,
    update_recording_fields,
)
from app.inngest.schemas import BlobVerificationResult, UploadConfirmedPayload
from app.services.oral_collector.constants import GCS_OC_BUCKET, GCS_OC_PROJECT
from app.services.oral_collector.gcs_utils import GCS_PUBLIC_BASE

logger = logging.getLogger(__name__)


async def _on_upload_failure(ctx: inngest.Context, _step: inngest.Step) -> None:
    fc = extract_failure_context(ctx, "Upload processing failed")

    await update_recording_fields(
        fc.recording_id,
        upload_status=UploadStatus.UPLOAD_FAILED,
        upload_error=fc.error_message,
    )

    if fc.user_id:
        await notify_user(
            fc.user_id,
            OCNotificationEvent.UPLOAD_FAILED,
            "Upload failed — keep local recording",
            f"Upload processing failed: {fc.error_message}. "
            "Please keep the local recording and retry the upload.",
        )


@inngest_client.create_function(
    fn_id="process-upload",
    trigger=inngest.TriggerEvent(event=OCRecordingEvent.UPLOAD_CONFIRMED),
    retries=3,
    on_failure=_on_upload_failure,  # type: ignore[arg-type]
)
async def process_upload_fn(ctx: inngest.Context, step: inngest.Step) -> str:
    """Process a recording upload: verify integrity, finalize status, notify."""
    payload = UploadConfirmedPayload.model_validate(ctx.event.data)

    async def _set_upload_metadata() -> str:
        async with AsyncSessionLocal() as db:
            recording = await db.get(OC_Recording, payload.recording_id)
            if not recording:
                raise inngest.NonRetriableError("Recording not found")
            gcs_url = f"{GCS_PUBLIC_BASE}{payload.expected_blob_path}"
            recording.gcs_url = gcs_url
            recording.uploaded_at = datetime.now(UTC)
            recording.upload_status = UploadStatus.UPLOADED
            recording.upload_error = None
            await db.commit()
            return gcs_url

    await step.run("set-upload-metadata", _set_upload_metadata)

    async def _verify_gcs_blob() -> dict[str, int]:
        from google.cloud import storage

        client = storage.Client(project=GCS_OC_PROJECT)
        bucket = client.bucket(GCS_OC_BUCKET)
        blob = bucket.blob(payload.expected_blob_path)

        if not blob.exists():
            raise inngest.NonRetriableError("Blob does not exist in GCS — upload may have failed")

        blob.reload()
        actual_size = blob.size or 0
        if payload.expected_size_bytes > 0 and actual_size != payload.expected_size_bytes:
            raise inngest.NonRetriableError(
                f"Size mismatch: expected {payload.expected_size_bytes}, got {actual_size}"
            )
        return BlobVerificationResult(size=actual_size).model_dump()

    blob_info = BlobVerificationResult.model_validate(
        await step.run("verify-gcs-blob", _verify_gcs_blob)
    )

    await step.run(
        "finalize-verified",
        lambda: update_recording_fields(payload.recording_id, upload_status=UploadStatus.VERIFIED),
    )

    async def _notify() -> None:
        await notify_user(
            payload.user_id,
            OCNotificationEvent.UPLOAD_VERIFIED,
            "Recording uploaded — safe to free device storage",
            f"Upload verified ({blob_info.size} bytes). You can safely delete the local recording.",
        )

    await step.run("notify-upload-complete", _notify)

    return UploadStatus.VERIFIED
