from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap
from app.services.common import get_or_raise


async def get_meaning_map_or_404(db: AsyncSession, map_id: str) -> MeaningMap:
    return await get_or_raise(db, MeaningMap, map_id, label="Meaning map")
