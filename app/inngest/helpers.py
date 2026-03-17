from dataclasses import dataclass
from typing import Any, cast

import inngest

from app.core.database import AsyncSessionLocal
from app.core.enums import UploadStatus
from app.db.models.oc_recording import OC_Recording
from app.services.notifications.create_notification import create_notification
from app.services.notifications.get_oc_app_id import get_oc_app_id


@dataclass(frozen=True)
class FailureContext:
    recording_id: str
    user_id: str
    error_message: str


def extract_failure_context(
    ctx: inngest.Context, default_error: str = "Unknown error"
) -> FailureContext:
    data = cast(dict[str, Any], ctx.event.data or {})
    original_event = cast(dict[str, Any], data.get("event", {}))
    event_data = cast(dict[str, Any], original_event.get("data", {}))
    error_info = cast(dict[str, Any], data.get("error", {}))
    return FailureContext(
        recording_id=str(event_data.get("recording_id", "")),
        user_id=str(event_data.get("user_id", "")),
        error_message=str(error_info.get("message", default_error)),
    )


async def update_recording_fields(recording_id: str, **fields: Any) -> None:
    async with AsyncSessionLocal() as db:
        recording = await db.get(OC_Recording, recording_id)
        if recording:
            for field, value in fields.items():
                setattr(recording, field, value)
            await db.commit()


async def check_recording_verified(recording_id: str) -> str:
    async with AsyncSessionLocal() as db:
        recording = await db.get(OC_Recording, recording_id)
        if not recording:
            raise inngest.NonRetriableError("Recording not found")
        if recording.upload_status != UploadStatus.VERIFIED:
            raise inngest.NonRetriableError(
                f"Recording upload_status is '{recording.upload_status}', "
                f"expected '{UploadStatus.VERIFIED}'"
            )
        if not recording.gcs_url:
            raise inngest.NonRetriableError("Recording has no GCS URL")
        return recording.gcs_url


async def notify_user(
    user_id: str,
    event_type: str,
    title: str,
    body: str,
) -> None:
    async with AsyncSessionLocal() as db:
        app_id = await get_oc_app_id(db)
        await create_notification(
            db,
            user_id=user_id,
            app_id=app_id,
            event_type=event_type,
            title=title,
            body=body,
        )
