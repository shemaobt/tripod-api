from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_health import PHInterview, PHReport


async def list_admin_dashboard(
    db: AsyncSession, *, limit: int = 200
) -> tuple[list[PHInterview], list[PHReport]]:
    """Return recent interviews (in_progress first, then most-recent completed) and
    the matching reports list for the dashboard view."""
    interviews_stmt = select(PHInterview).order_by(PHInterview.created_at.desc()).limit(limit)
    interviews_result = await db.execute(interviews_stmt)
    interviews = list(interviews_result.scalars().all())

    if not interviews:
        return [], []

    interview_ids = [i.id for i in interviews]
    reports_stmt = select(PHReport).where(PHReport.interview_id.in_(interview_ids))
    reports_result = await db.execute(reports_stmt)
    reports = list(reports_result.scalars().all())
    return interviews, reports
