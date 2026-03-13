from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap, Pericope


async def list_meaning_maps(
    db: AsyncSession,
    *,
    book_id: str | None = None,
    chapter: int | None = None,
    status: str | None = None,
) -> list:

    cols = [c for c in MeaningMap.__table__.columns if c.key != "data"]
    stmt = select(*cols).join(Pericope, MeaningMap.pericope_id == Pericope.id)
    if book_id:
        stmt = stmt.where(Pericope.book_id == book_id)
    if chapter is not None:
        stmt = stmt.where(Pericope.chapter_start == chapter)
    if status:
        stmt = stmt.where(MeaningMap.status == status)
    stmt = stmt.order_by(MeaningMap.created_at.desc())
    result = await db.execute(stmt)
    return list(result.mappings().all())
