from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.book_context import BCDSectionFeedback
from app.services.book_context.get_bcd import get_bcd_or_404


async def add_feedback(
    db: AsyncSession,
    bcd_id: str,
    section_key: str,
    author_id: str,
    content: str,
) -> BCDSectionFeedback:
    await get_bcd_or_404(db, bcd_id)

    feedback = BCDSectionFeedback(
        bcd_id=bcd_id,
        section_key=section_key,
        author_id=author_id,
        content=content,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback
