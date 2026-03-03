from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMapFeedback


async def list_feedback(
    db: AsyncSession, meaning_map_id: str
) -> list[MeaningMapFeedback]:
    stmt = (
        select(MeaningMapFeedback)
        .where(MeaningMapFeedback.meaning_map_id == meaning_map_id)
        .order_by(MeaningMapFeedback.created_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
