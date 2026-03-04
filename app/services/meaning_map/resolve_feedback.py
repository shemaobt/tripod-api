from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.meaning_map import MeaningMapFeedback


async def resolve_feedback(
    db: AsyncSession, meaning_map_id: str, feedback_id: str
) -> MeaningMapFeedback:
    stmt = select(MeaningMapFeedback).where(
        MeaningMapFeedback.id == feedback_id,
        MeaningMapFeedback.meaning_map_id == meaning_map_id,
    )
    result = await db.execute(stmt)
    fb = result.scalar_one_or_none()
    if fb is None:
        raise NotFoundError(f"Feedback {feedback_id} not found")
    fb.resolved = True
    await db.commit()
    await db.refresh(fb)
    return fb
