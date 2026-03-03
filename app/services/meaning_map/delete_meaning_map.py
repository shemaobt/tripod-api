from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.models.meaning_map import MeaningMap


async def delete_meaning_map(db: AsyncSession, mm: MeaningMap, user_id: str) -> None:
    if mm.status != "draft":
        raise AuthorizationError("Only draft meaning maps can be deleted")
    if mm.analyst_id != user_id:
        raise AuthorizationError("Only the analyst who created the map can delete it")
    await db.delete(mm)
    await db.commit()
