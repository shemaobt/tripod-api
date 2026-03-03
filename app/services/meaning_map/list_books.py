from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import BibleBook


async def list_books(db: AsyncSession) -> list[BibleBook]:
    stmt = select(BibleBook).order_by(BibleBook.order)
    result = await db.execute(stmt)
    return list(result.scalars().all())
