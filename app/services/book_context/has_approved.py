from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BCDStatus, BookContextDocument


async def has_approved_bcd(db: AsyncSession, book_id: str) -> bool:
    """Check whether a book has at least one approved Book Context Document."""
    result = await db.execute(
        select(BookContextDocument.id).where(
            BookContextDocument.book_id == book_id,
            BookContextDocument.status == BCDStatus.APPROVED,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None
