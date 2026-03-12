from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.meaning_map import BibleBook, Pericope

async def get_pericope_with_book(db: AsyncSession, pericope_id: str) -> tuple[Pericope, BibleBook]:

    stmt = (
        select(Pericope, BibleBook)
        .join(BibleBook, Pericope.book_id == BibleBook.id)
        .where(Pericope.id == pericope_id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        raise NotFoundError(f"Pericope {pericope_id} not found")
    return row[0], row[1]
