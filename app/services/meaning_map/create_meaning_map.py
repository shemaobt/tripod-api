from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap


async def create_meaning_map(
    db: AsyncSession,
    pericope_id: str,
    analyst_id: str,
    data: dict,
    status: str = "draft",
) -> MeaningMap:
    mm = MeaningMap(
        pericope_id=pericope_id,
        analyst_id=analyst_id,
        data=data,
        status=status,
    )
    db.add(mm)
    await db.commit()
    await db.refresh(mm)
    return mm
