from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.project_health._deps import ph_admin
from app.core.database import get_db
from app.models.project_health import AdminReportResponse, TeamReportResponse
from app.services import project_health_service as ph_service

router = APIRouter()


@router.get("/reports/team/{report_id}", response_model=TeamReportResponse)
async def get_team_report_endpoint(
    report_id: str, db: AsyncSession = Depends(get_db)
) -> TeamReportResponse:
    return await ph_service.get_team_report(db, report_id)


@router.get(
    "/reports/admin/{report_id}",
    response_model=AdminReportResponse,
    dependencies=[ph_admin],
)
async def get_admin_report_endpoint(
    report_id: str, db: AsyncSession = Depends(get_db)
) -> AdminReportResponse:
    return await ph_service.get_admin_report(db, report_id)
