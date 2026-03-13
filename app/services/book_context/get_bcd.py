from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BookContextDocument
from app.services.common import get_or_raise


async def get_bcd(db: AsyncSession, bcd_id: str) -> BookContextDocument | None:
    result = await db.execute(select(BookContextDocument).where(BookContextDocument.id == bcd_id))
    return result.scalar_one_or_none()


async def get_bcd_or_404(db: AsyncSession, bcd_id: str) -> BookContextDocument:
    return await get_or_raise(db, BookContextDocument, bcd_id, label="Book Context Document")
