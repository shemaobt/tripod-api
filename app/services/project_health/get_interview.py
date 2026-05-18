from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.project_health import PHInterview


async def get_interview_or_404(db: AsyncSession, interview_id: str) -> PHInterview:
    """Fetch a single interview row by id or raise NotFoundError."""
    stmt = select(PHInterview).where(PHInterview.id == interview_id)
    result = await db.execute(stmt)
    interview = result.scalar_one_or_none()
    if interview is None:
        raise NotFoundError("Interview not found")
    return interview
