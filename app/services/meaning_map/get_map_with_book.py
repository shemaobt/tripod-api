from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.meaning_map import BibleBook, MeaningMap, Pericope

async def get_map_with_book(db: AsyncSession, map_id: str) -> tuple[MeaningMap, BibleBook]:

    stmt = (
        select(MeaningMap, BibleBook)
        .join(Pericope, MeaningMap.pericope_id == Pericope.id)
        .join(BibleBook, Pericope.book_id == BibleBook.id)
        .where(MeaningMap.id == map_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        raise NotFoundError(f"Meaning map {map_id} not found")
    return row[0], row[1]
