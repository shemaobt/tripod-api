from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.meaning_map import MeaningMap


async def lock_map(db: AsyncSession, mm: MeaningMap, user_id: str) -> MeaningMap:
    if mm.locked_by and mm.locked_by != user_id:
        raise ConflictError("This meaning map is already locked by another user")
    if mm.status == "approved":
        raise ConflictError("Cannot lock an approved meaning map")
    mm.locked_by = user_id
    mm.locked_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(mm)
    return mm
