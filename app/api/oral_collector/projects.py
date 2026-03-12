from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.db.models.project import ProjectUserAccess
from app.models.oc_project import (
    OCProjectListResponse,
    OCProjectStatsResponse,
)
from app.services.oral_collector import project_service

projects_router = APIRouter()


@projects_router.get("", response_model=list[OCProjectListResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OCProjectListResponse]:
    """List projects the current user has access to, with member counts."""
    projects = await project_service.list_user_projects(db, user.id)
    if not projects:
        return []

    project_ids = [p.id for p in projects]
    count_stmt = (
        select(
            ProjectUserAccess.project_id,
            func.count().label("member_count"),
        )
        .where(ProjectUserAccess.project_id.in_(project_ids))
        .group_by(ProjectUserAccess.project_id)
    )
    result = await db.execute(count_stmt)
    counts = {row.project_id: row.member_count for row in result.all()}

    return [
        OCProjectListResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            language_id=p.language_id,
            latitude=p.latitude,
            longitude=p.longitude,
            location_display_name=p.location_display_name,
            created_at=p.created_at,
            updated_at=p.updated_at,
            member_count=counts.get(p.id, 0),
        )
        for p in projects
    ]


@projects_router.get("/{project_id}/stats", response_model=OCProjectStatsResponse)
async def get_project_stats(
    project_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OCProjectStatsResponse:
    """Get recording stats for a project."""
    stats = await project_service.get_project_stats(db, project_id)
    return OCProjectStatsResponse(**stats)
