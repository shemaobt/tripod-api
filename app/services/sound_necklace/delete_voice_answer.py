from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.sound_necklace import SnVoiceAnswer
from app.services.oral_collector import gcs_utils
from app.services.sound_necklace.constants import GCS_SN_BUCKET


async def delete_voice_answer(db: AsyncSession, session_id: str, resource_path: str) -> None:
    """Remove one voice answer — the object and its row.

    A path that was never recorded is not an error: the caller's goal (no answer at this
    path) is already met, so deleting a missing answer is a no-op. The object is deleted
    before the row, and the GCS delete is itself idempotent, so a failure after the
    object is gone leaves no row pointing at a missing object.
    """
    answer = await db.get(SnVoiceAnswer, (session_id, resource_path))
    if answer is None:
        return

    await gcs_utils.delete_gcs_object(GCS_SN_BUCKET, answer.storage_key)
    await db.delete(answer)
    await db.commit()
