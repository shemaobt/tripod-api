from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.book_context import BCDSectionFeedback


async def resolve_feedback(
    db: AsyncSession,
    bcd_id: str,
    feedback_id: str,
) -> BCDSectionFeedback:
    result = await db.execute(
        select(BCDSectionFeedback).where(
            BCDSectionFeedback.id == feedback_id,
            BCDSectionFeedback.bcd_id == bcd_id,
        )
    )
    feedback = result.scalar_one_or_none()
    if not feedback:
        raise NotFoundError("Feedback not found.")

    feedback.resolved = True
    await db.commit()
    await db.refresh(feedback)
    return feedback
