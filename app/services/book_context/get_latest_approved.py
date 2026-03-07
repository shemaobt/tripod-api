from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BCDStatus, BookContextDocument


async def get_latest_approved(db: AsyncSession, book_id: str) -> BookContextDocument | None:
    """Return the latest approved BCD for a book.

    Prefers explicitly active, falls back to latest approved.
    """
    # First: check for an explicitly active + approved BCD
    result = await db.execute(
        select(BookContextDocument)
        .where(
            BookContextDocument.book_id == book_id,
            BookContextDocument.is_active,
            BookContextDocument.status == BCDStatus.APPROVED,
        )
        .limit(1)
    )
    active = result.scalar_one_or_none()
    if active:
        return active

    # Fallback: latest approved version
    result = await db.execute(
        select(BookContextDocument)
        .where(
            BookContextDocument.book_id == book_id,
            BookContextDocument.status == BCDStatus.APPROVED,
        )
        .order_by(BookContextDocument.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
