from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.sound_necklace import SnVoiceAnswer
from app.services.oral_collector import gcs_utils
from app.services.sound_necklace.constants import DOWNLOAD_URL_EXPIRY_MINUTES, GCS_SN_BUCKET


async def voice_answer_url(db: AsyncSession, session_id: str, resource_path: str) -> str:
    """A short-lived signed GET for one voice answer.

    The bytes are never proxied — the recording is served straight from the private
    bucket. This is the audit point for a voice answer.
    """
    answer = await db.get(SnVoiceAnswer, (session_id, resource_path))
    if answer is None:
        raise NotFoundError("No voice answer at this path")

    return await gcs_utils.generate_signed_download_url(
        GCS_SN_BUCKET,
        answer.storage_key,
        expiry_minutes=DOWNLOAD_URL_EXPIRY_MINUTES,
    )
