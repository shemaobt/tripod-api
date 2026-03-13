from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.db.models.meaning_map import BibleBook, MeaningMap, MeaningMapStatus, Pericope
from app.models.meaning_map import AnalystSummary, DashboardSummaryResponse


async def get_dashboard_summary(db: AsyncSession) -> DashboardSummaryResponse:

    analyst = User.__table__.alias("analyst")

    stmt = (
        select(
            func.count(distinct(Pericope.id)).label("total"),
            func.count(
                distinct(
                    case(
                        (MeaningMap.status == MeaningMapStatus.DRAFT, Pericope.id),
                    )
                )
            ).label("draft"),
            func.count(
                distinct(
                    case(
                        (MeaningMap.status == MeaningMapStatus.CROSS_CHECK, Pericope.id),
                    )
                )
            ).label("cross_check"),
            func.count(
                distinct(
                    case(
                        (MeaningMap.status == MeaningMapStatus.APPROVED, Pericope.id),
                    )
                )
            ).label("approved"),
            func.count(distinct(case((MeaningMap.id.is_(None), Pericope.id)))).label("unstarted"),
            func.count(distinct(case((BibleBook.is_enabled.is_(True), BibleBook.id)))).label(
                "enabled_books"
            ),
        )
        .select_from(Pericope)
        .join(BibleBook, Pericope.book_id == BibleBook.id)
        .outerjoin(MeaningMap, MeaningMap.pericope_id == Pericope.id)
        .where(BibleBook.is_enabled.is_(True))
    )
    result = await db.execute(stmt)
    row = result.one()

    analyst_stmt = (
        select(
            analyst.c.display_name.label("name"),
            func.count(MeaningMap.id).label("assigned"),
            func.count(case((MeaningMap.status == MeaningMapStatus.DRAFT, 1))).label("draft"),
            func.count(
                case(
                    (MeaningMap.status == MeaningMapStatus.CROSS_CHECK, 1),
                )
            ).label("cross_check"),
            func.count(case((MeaningMap.status == MeaningMapStatus.APPROVED, 1))).label("approved"),
        )
        .select_from(MeaningMap)
        .join(Pericope, MeaningMap.pericope_id == Pericope.id)
        .join(BibleBook, Pericope.book_id == BibleBook.id)
        .join(analyst, analyst.c.id == MeaningMap.analyst_id)
        .where(BibleBook.is_enabled.is_(True))
        .group_by(analyst.c.display_name)
        .order_by(func.count(MeaningMap.id).desc())
    )
    analyst_result = await db.execute(analyst_stmt)
    analysts = [
        AnalystSummary(
            name=r.name or "Unknown",
            assigned=r.assigned,
            draft=r.draft,
            cross_check=r.cross_check,
            approved=r.approved,
        )
        for r in analyst_result.all()
    ]

    return DashboardSummaryResponse(
        total=row.total,
        draft=row.draft,
        cross_check=row.cross_check,
        approved=row.approved,
        unstarted=row.unstarted,
        enabled_books=row.enabled_books,
        analysts=analysts,
    )
