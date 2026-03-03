from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.meaning_map import BibleBook


async def get_book_or_404(db: AsyncSession, book_id: str) -> BibleBook:
    stmt = select(BibleBook).where(BibleBook.id == book_id)
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()
    if book is None:
        raise NotFoundError(f"Bible book {book_id} not found")
    return book
