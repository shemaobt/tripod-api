from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.meaning_map import Pericope


async def get_pericope_or_404(db: AsyncSession, pericope_id: str) -> Pericope:
    stmt = select(Pericope).where(Pericope.id == pericope_id)
    result = await db.execute(stmt)
    pericope = result.scalar_one_or_none()
    if pericope is None:
        raise NotFoundError(f"Pericope {pericope_id} not found")
    return pericope
