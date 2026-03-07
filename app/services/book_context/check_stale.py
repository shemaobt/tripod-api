from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap, Pericope
from app.services.book_context.get_latest_approved import get_latest_approved


async def check_bcd_staleness(
    db: AsyncSession,
    meaning_map: MeaningMap,
) -> dict:
    result = await db.execute(
        select(Pericope.book_id).where(Pericope.id == meaning_map.pericope_id)
    )
    book_id = result.scalar_one_or_none()
    if not book_id:
        return {"is_stale": False}

    bcd = await get_latest_approved(db, book_id)
    if not bcd:
        return {"is_stale": False}

    if meaning_map.bcd_version_at_creation is None:
        return {"is_stale": False}

    if bcd.version > meaning_map.bcd_version_at_creation:
        return {"is_stale": True, "current_version": bcd.version}

    return {"is_stale": False}
