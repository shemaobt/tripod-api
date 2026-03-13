from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import Pericope
from app.services.common import get_or_raise


async def get_pericope_or_404(db: AsyncSession, pericope_id: str) -> Pericope:
    return await get_or_raise(db, Pericope, pericope_id, label="Pericope")
