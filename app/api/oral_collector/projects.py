from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user, require_platform_admin
from app.core.database import get_db
from app.db.models.auth import User
from app.models.oc_project import (
    OCAddMemberRequest,
    OCProjectStatsResponse,
    OCProjectUserResponse,
)
from app.models.project import ProjectResponse
from app.services.oral_collector import project_service

projects_router = APIRouter()


# ---------------------------------------------------------------------------
# Project membership endpoints  (prefix: /api/oc/projects)
# ---------------------------------------------------------------------------


@projects_router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectResponse]:
    """List all projects the current user is a member of."""
    projects = await project_service.list_user_projects(db, user.id)
    return [ProjectResponse.model_validate(p) for p in projects]


@projects_router.get("/{project_id}/members", response_model=list[OCProjectUserResponse])
async def list_members(
    project_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OCProjectUserResponse]:
    """List all members of a project."""
    members = await project_service.get_project_members(db, project_id)
    return [OCProjectUserResponse.model_validate(m) for m in members]


@projects_router.post(
    "/{project_id}/members",
    response_model=OCProjectUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    project_id: str,
    payload: OCAddMemberRequest,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> OCProjectUserResponse:
    """Add a member to a project (admin only)."""
    member = await project_service.add_member(
        db, project_id, payload.user_id, payload.role
    )
    return OCProjectUserResponse.model_validate(member)


@projects_router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    project_id: str,
    user_id: str,
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a member from a project (admin only)."""
    await project_service.remove_member(db, project_id, user_id)


@projects_router.get("/{project_id}/stats", response_model=OCProjectStatsResponse)
async def get_project_stats(
    project_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OCProjectStatsResponse:
    """Get recording stats for a project."""
    stats = await project_service.get_project_stats(db, project_id)
    return OCProjectStatsResponse(**stats)
