from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap


async def create_meaning_map(
    db: AsyncSession,
    pericope_id: str,
    analyst_id: str,
    data: dict,
    status: str = "draft",
    bcd_version_at_creation: int | None = None,
) -> MeaningMap:
    mm = MeaningMap(
        pericope_id=pericope_id,
        analyst_id=analyst_id,
        data=data,
        status=status,
        bcd_version_at_creation=bcd_version_at_creation,
    )
    db.add(mm)
    await db.commit()
    await db.refresh(mm)
    return mm
