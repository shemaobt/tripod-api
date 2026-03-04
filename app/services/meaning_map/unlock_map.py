from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.models.meaning_map import MeaningMap


async def unlock_map(
    db: AsyncSession, mm: MeaningMap, user_id: str, *, is_admin: bool = False
) -> MeaningMap:
    if not mm.locked_by:
        return mm
    if mm.locked_by != user_id and not is_admin:
        raise AuthorizationError("Only the lock holder or an admin can unlock")
    mm.locked_by = None
    mm.locked_at = None
    await db.commit()
    await db.refresh(mm)
    return mm
