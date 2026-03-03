from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.db.models.meaning_map import MeaningMap, Pericope
from app.models.meaning_map import PericopeWithStatusResponse


async def list_pericopes(
    db: AsyncSession, book_id: str, chapter: int | None = None
) -> list[PericopeWithStatusResponse]:
    analyst = User.__table__.alias("analyst")
    lock_user = User.__table__.alias("lock_user")

    stmt = (
        select(
            Pericope,
            MeaningMap.id.label("meaning_map_id"),
            MeaningMap.status,
            MeaningMap.locked_by,
            lock_user.c.display_name.label("locked_by_name"),
            analyst.c.display_name.label("analyst_name"),
        )
        .outerjoin(MeaningMap, MeaningMap.pericope_id == Pericope.id)
        .outerjoin(analyst, analyst.c.id == MeaningMap.analyst_id)
        .outerjoin(lock_user, lock_user.c.id == MeaningMap.locked_by)
    )

    if chapter is not None:
        stmt = stmt.where(
            Pericope.book_id == book_id,
            Pericope.chapter_start <= chapter,
            Pericope.chapter_end >= chapter,
        )
    else:
        stmt = stmt.where(Pericope.book_id == book_id)

    stmt = stmt.order_by(Pericope.chapter_start, Pericope.verse_start)
    result = await db.execute(stmt)
    rows = result.all()

    out: list[PericopeWithStatusResponse] = []
    for row in rows:
        pericope = row[0]
        resp = PericopeWithStatusResponse.model_validate(pericope)
        resp.meaning_map_id = row.meaning_map_id
        resp.status = row.status
        resp.locked_by = row.locked_by
        resp.locked_by_name = row.locked_by_name
        resp.analyst_name = row.analyst_name
        out.append(resp)
    return out
