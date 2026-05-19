from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_health import PHInterview
from app.services.project_health.get_interview import get_interview_or_404


async def get_admin_interview_detail(db: AsyncSession, interview_id: str) -> PHInterview:
    """Fetch a full PHInterview row for admin read-only inspection.

    Wraps ``get_interview_or_404`` so the admin transcript endpoint has its
    own explicit service entry point, separate from the team-facing flow
    that runs behind the interview-token dependency.
    """
    return await get_interview_or_404(db, interview_id)
