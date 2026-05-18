from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.project_health import PHInterview


async def get_interview_or_404(
    db: AsyncSession, interview_id: str, *, for_update: bool = False
) -> PHInterview:
    """Fetch a single interview row by id or raise NotFoundError.

    When `for_update=True`, the row is locked via `SELECT ... FOR UPDATE` so
    concurrent writers serialize behind the same row. The lock is released
    when the session commits or rolls back.
    """
    stmt = select(PHInterview).where(PHInterview.id == interview_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    interview = result.scalar_one_or_none()
    if interview is None:
        raise NotFoundError("Interview not found")
    return interview
