from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.project_health.get_interview import get_interview_or_404


async def delete_interview(db: AsyncSession, interview_id: str) -> None:
    """Delete a PHInterview row. The PHReport row (if any) is removed by the
    ``ondelete="CASCADE"`` foreign key on ``PHReport.interview_id``."""
    interview = await get_interview_or_404(db, interview_id)
    await db.delete(interview)
    await db.commit()
