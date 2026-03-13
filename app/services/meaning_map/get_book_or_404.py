from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import BibleBook
from app.services.common import get_or_raise


async def get_book_or_404(db: AsyncSession, book_id: str) -> BibleBook:
    return await get_or_raise(db, BibleBook, book_id, label="Bible book")
