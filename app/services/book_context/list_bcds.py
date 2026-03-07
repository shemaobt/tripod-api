from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BookContextDocument


async def list_bcds(
    db: AsyncSession,
    book_id: str | None = None,
) -> list[BookContextDocument]:
    stmt = select(BookContextDocument).order_by(BookContextDocument.created_at.desc())
    if book_id:
        stmt = stmt.where(BookContextDocument.book_id == book_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
