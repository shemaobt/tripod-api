from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.models.meaning_map import MeaningMap


async def update_meaning_map_data(
    db: AsyncSession, mm: MeaningMap, data: dict, user_id: str
) -> MeaningMap:
    if mm.locked_by and mm.locked_by != user_id:
        raise AuthorizationError("This meaning map is locked by another user")
    if mm.status == "approved":
        raise AuthorizationError("Cannot edit an approved meaning map")
    mm.data = data
    await db.commit()
    await db.refresh(mm)
    return mm
