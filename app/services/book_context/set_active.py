from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.book_context import BCDStatus, BookContextDocument
from app.services.book_context.get_bcd import get_bcd_or_404


async def set_active_bcd(
    db: AsyncSession,
    bcd_id: str,
) -> BookContextDocument:
    """Mark a BCD as the active version for its book, deactivating all others."""
    bcd = await get_bcd_or_404(db, bcd_id)

    if bcd.status == BCDStatus.GENERATING:
        raise ConflictError("Cannot set a generating document as active.")

    # Deactivate all other BCDs for this book
    await db.execute(
        update(BookContextDocument)
        .where(
            BookContextDocument.book_id == bcd.book_id,
            BookContextDocument.id != bcd_id,
            BookContextDocument.is_active == True,
        )
        .values(is_active=False)
    )

    bcd.is_active = True
    await db.commit()
    await db.refresh(bcd)
    return bcd
