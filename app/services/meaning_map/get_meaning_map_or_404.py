from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.meaning_map import MeaningMap


async def get_meaning_map_or_404(db: AsyncSession, map_id: str) -> MeaningMap:
    stmt = select(MeaningMap).where(MeaningMap.id == map_id)
    result = await db.execute(stmt)
    mm = result.scalar_one_or_none()
    if mm is None:
        raise NotFoundError(f"Meaning map {map_id} not found")
    return mm
