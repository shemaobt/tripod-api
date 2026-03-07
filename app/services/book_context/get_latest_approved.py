from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BCDStatus, BookContextDocument


async def get_latest_approved(
    db: AsyncSession, book_id: str
) -> BookContextDocument | None:
    """Return the active BCD for a book. Prefers explicitly active, falls back to latest by version."""
    # First: check for an explicitly active BCD (any non-generating status)
    result = await db.execute(
        select(BookContextDocument)
        .where(
            BookContextDocument.book_id == book_id,
            BookContextDocument.is_active == True,
            BookContextDocument.status != BCDStatus.GENERATING,
        )
        .limit(1)
    )
    active = result.scalar_one_or_none()
    if active:
        return active

    # Fallback: latest non-generating version
    result = await db.execute(
        select(BookContextDocument)
        .where(
            BookContextDocument.book_id == book_id,
            BookContextDocument.status != BCDStatus.GENERATING,
        )
        .order_by(BookContextDocument.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
