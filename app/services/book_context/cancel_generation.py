from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.book_context import BCDGenerationLog, BCDStatus
from app.services.book_context.get_bcd import get_bcd_or_404


async def cancel_generation(db: AsyncSession, bcd_id: str) -> str:
    """Cancel an in-progress generation by deleting the BCD. Returns the book_id."""
    bcd = await get_bcd_or_404(db, bcd_id)

    if bcd.status != BCDStatus.GENERATING:
        raise ConflictError("This version is not currently generating.")

    book_id = bcd.book_id

    await db.execute(delete(BCDGenerationLog).where(BCDGenerationLog.bcd_id == bcd_id))
    await db.delete(bcd)
    await db.commit()

    return book_id
