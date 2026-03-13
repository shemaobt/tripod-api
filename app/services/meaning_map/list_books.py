from sqlalchemy import func, outerjoin, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import BibleBook, MeaningMap, MeaningMapStatus, Pericope
from app.models.meaning_map import BibleBookResponse


async def list_books(db: AsyncSession) -> list[BibleBookResponse]:

    j = outerjoin(Pericope, MeaningMap, Pericope.id == MeaningMap.pericope_id)

    counts_q = (
        select(
            Pericope.book_id,
            func.count(Pericope.id).label("pericope_count"),
            func.count(MeaningMap.id)
            .filter(MeaningMap.status == MeaningMapStatus.APPROVED)
            .label("approved_count"),
        )
        .select_from(j)
        .group_by(Pericope.book_id)
        .subquery()
    )

    stmt = (
        select(
            BibleBook,
            func.coalesce(counts_q.c.pericope_count, 0).label("pericope_count"),
            func.coalesce(counts_q.c.approved_count, 0).label("approved_count"),
        )
        .outerjoin(counts_q, BibleBook.id == counts_q.c.book_id)
        .order_by(BibleBook.order)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        BibleBookResponse(
            id=book.id,
            name=book.name,
            abbreviation=book.abbreviation,
            testament=book.testament,
            order=book.order,
            chapter_count=book.chapter_count,
            is_enabled=book.is_enabled,
            pericope_count=pericope_count,
            approved_count=approved_count,
            created_at=book.created_at,
        )
        for book, pericope_count, approved_count in rows
    ]
