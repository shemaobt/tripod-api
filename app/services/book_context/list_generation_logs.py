from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BCDGenerationLog


async def list_generation_logs(
    db: AsyncSession,
    bcd_id: str,
) -> list[BCDGenerationLog]:
    result = await db.execute(
        select(BCDGenerationLog)
        .where(BCDGenerationLog.bcd_id == bcd_id)
        .order_by(BCDGenerationLog.step_order)
    )
    return list(result.scalars().all())
