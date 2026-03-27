from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.book_context import BCDStatus, BookContextDocument

LOCK_TIMEOUT = timedelta(hours=4)


async def lock_bcd(db: AsyncSession, bcd: BookContextDocument, user_id: str) -> BookContextDocument:
    if bcd.status != BCDStatus.DRAFT:
        raise ConflictError("Can only lock a document in draft status.")
    if bcd.locked_by and bcd.locked_by != user_id:
        locked_at = (
            bcd.locked_at.replace(tzinfo=UTC)
            if bcd.locked_at and bcd.locked_at.tzinfo is None
            else bcd.locked_at
        )
        if locked_at and (datetime.now(UTC) - locked_at) > LOCK_TIMEOUT:
            pass
        else:
            raise ConflictError("This document is already locked by another user.")
    bcd.locked_by = user_id
    bcd.locked_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(bcd)
    return bcd
