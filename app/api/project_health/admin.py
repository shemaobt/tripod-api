from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.project_health._deps import ph_admin
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.project_health import (
    AdminDashboardResponse,
    AdminInviteRequest,
    AdminInviteResponse,
    InterviewCompleteResponse,
    InterviewSummary,
    ReportSummary,
)
from app.services import project_health_service as ph_service
from app.services.project_health.complete_interview import InterviewIncompleteError

router = APIRouter()


@router.get(
    "/admin/dashboard",
    response_model=AdminDashboardResponse,
    dependencies=[ph_admin],
)
async def admin_dashboard_endpoint(
    db: AsyncSession = Depends(get_db),
) -> AdminDashboardResponse:
    interviews, reports = await ph_service.list_admin_dashboard(db)
    return AdminDashboardResponse(
        interviews=[InterviewSummary.model_validate(i) for i in interviews],
        reports=[ReportSummary.model_validate(r) for r in reports],
    )


@router.post(
    "/admin/invites",
    response_model=AdminInviteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[ph_admin],
)
async def invite_admin_endpoint(
    payload: AdminInviteRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> AdminInviteResponse:
    return await ph_service.invite_admin(db, email=str(payload.email), invited_by_user_id=actor.id)


@router.post(
    "/admin/interviews/{interview_id}/complete",
    response_model=InterviewCompleteResponse,
    dependencies=[ph_admin],
)
async def admin_force_complete_interview_endpoint(
    interview_id: str,
    db: AsyncSession = Depends(get_db),
) -> InterviewCompleteResponse | JSONResponse:
    try:
        report_id, team_report = await ph_service.complete_interview(db, interview_id, force=True)
    except InterviewIncompleteError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=exc.payload.model_dump(),
        )
    return InterviewCompleteResponse(report_id=report_id, team_report=team_report)
