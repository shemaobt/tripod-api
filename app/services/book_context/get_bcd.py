from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.book_context import BookContextDocument


async def get_bcd(db: AsyncSession, bcd_id: str) -> BookContextDocument | None:
    result = await db.execute(
        select(BookContextDocument).where(BookContextDocument.id == bcd_id)
    )
    return result.scalar_one_or_none()


async def get_bcd_or_404(db: AsyncSession, bcd_id: str) -> BookContextDocument:
    bcd = await get_bcd(db, bcd_id)
    if not bcd:
        raise NotFoundError(f"Book Context Document {bcd_id} not found.")
    return bcd
