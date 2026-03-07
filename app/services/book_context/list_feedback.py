from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BCDSectionFeedback


async def list_feedback(
    db: AsyncSession,
    bcd_id: str,
) -> list[BCDSectionFeedback]:
    result = await db.execute(
        select(BCDSectionFeedback)
        .where(BCDSectionFeedback.bcd_id == bcd_id)
        .order_by(BCDSectionFeedback.created_at)
    )
    return list(result.scalars().all())
