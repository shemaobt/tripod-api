from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.project_health import PHInterview, PHReport
from app.models.project_health import (
    AdminReport,
    AdminReportResponse,
    TeamReport,
)


async def get_admin_report(db: AsyncSession, report_id: str) -> AdminReportResponse:
    """Return the full team + admin report payload for admin consumers."""
    report_stmt = select(PHReport).where(PHReport.id == report_id)
    report_row = (await db.execute(report_stmt)).scalar_one_or_none()
    if report_row is None:
        raise NotFoundError("Report not found")

    interview_stmt = select(PHInterview).where(
        PHInterview.id == report_row.interview_id
    )
    interview_row = (await db.execute(interview_stmt)).scalar_one_or_none()
    if interview_row is None:
        raise NotFoundError("Interview not found")

    return AdminReportResponse(
        id=report_row.id,
        interview_id=report_row.interview_id,
        language=interview_row.language,
        team_report=TeamReport.model_validate(report_row.team_report),
        admin_report=AdminReport.model_validate(report_row.admin_report),
        created_at=report_row.created_at,
    )
