from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap, Pericope
from app.models.book_context import StalenessCheckResponse
from app.services.book_context.get_latest_approved import get_latest_approved


async def check_bcd_staleness(
    db: AsyncSession,
    meaning_map: MeaningMap,
) -> StalenessCheckResponse:
    result = await db.execute(
        select(Pericope.book_id).where(Pericope.id == meaning_map.pericope_id)
    )
    book_id = result.scalar_one_or_none()
    if not book_id:
        return StalenessCheckResponse(is_stale=False)

    bcd = await get_latest_approved(db, book_id)
    if not bcd:
        return StalenessCheckResponse(is_stale=False)

    if meaning_map.bcd_version_at_creation is None:
        return StalenessCheckResponse(is_stale=False)

    if bcd.version > meaning_map.bcd_version_at_creation:
        return StalenessCheckResponse(is_stale=True, current_version=bcd.version)

    return StalenessCheckResponse(is_stale=False)
