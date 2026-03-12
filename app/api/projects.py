from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError
from app.db.models.auth import User
from app.db.models.project import Project
from app.models.phase import AttachPhaseRequest, ProjectPhaseResponse, ProjectPhaseStatusUpdate
from app.models.project import (
    ProjectCreate,
    ProjectGrantOrganizationAccess,
    ProjectGrantUserAccess,
    ProjectLocationUpdate,
    ProjectOrganizationAccessDetailResponse,
    ProjectOrganizationAccessResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectUserAccessDetailResponse,
    ProjectUserAccessResponse,
)
from app.services import phase_service, project_service

router = APIRouter()

async def _assert_project_access(db: AsyncSession, user: User, project_id: str) -> None:

    if user.is_platform_admin:
        return
    allowed = await project_service.can_access_project(db, user.id, project_id)
    if not allowed:
        raise AuthorizationError("You do not have access to this project")

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    language_id: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectResponse]:
    if user.is_platform_admin:
        result = await db.execute(select(Project).order_by(Project.name))
        projects = list(result.scalars().unique().all())
    else:
        projects = await project_service.list_projects_accessible_to_user(db, user.id)
    if language_id is not None:
        projects = [p for p in projects if p.language_id == language_id]
    return [ProjectResponse.model_validate(p) for p in projects]

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = await project_service.create_project(
        db,
        name=payload.name,
        language_id=payload.language_id,
        description=payload.description,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_display_name=payload.location_display_name,
        creator_user_id=str(user.id),
    )
    return ProjectResponse.model_validate(project)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = await project_service.get_project_or_404(db, project_id)
    await _assert_project_access(db, user, project_id)
    return ProjectResponse.model_validate(project)

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    await _assert_project_access(db, user, project_id)
    project = await project_service.update_project(
        db,
        project_id,
        name=payload.name,
        description=payload.description,
        language_id=payload.language_id,
    )
    return ProjectResponse.model_validate(project)

@router.patch("/{project_id}/location", response_model=ProjectResponse)
async def update_project_location(
    project_id: str,
    payload: ProjectLocationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    await _assert_project_access(db, user, project_id)
    project = await project_service.update_project_location(
        db,
        project_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_display_name=payload.location_display_name,
    )
    return ProjectResponse.model_validate(project)

@router.post(
    "/{project_id}/access/users",
    response_model=ProjectUserAccessResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_user_access(
    project_id: str,
    payload: ProjectGrantUserAccess,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectUserAccessResponse:
    await _assert_project_access(db, actor, project_id)
    await project_service.get_project_or_404(db, project_id)
    access = await project_service.grant_user_access(db, project_id, payload.user_id)
    return ProjectUserAccessResponse.model_validate(access)

@router.post(
    "/{project_id}/access/organizations",
    response_model=ProjectOrganizationAccessResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_organization_access(
    project_id: str,
    payload: ProjectGrantOrganizationAccess,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectOrganizationAccessResponse:
    await _assert_project_access(db, actor, project_id)
    await project_service.get_project_or_404(db, project_id)
    access = await project_service.grant_organization_access(
        db, project_id, payload.organization_id
    )
    return ProjectOrganizationAccessResponse.model_validate(access)

@router.get(
    "/{project_id}/access/users",
    response_model=list[ProjectUserAccessDetailResponse],
)
async def list_user_access(
    project_id: str,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectUserAccessDetailResponse]:
    await _assert_project_access(db, actor, project_id)
    await project_service.get_project_or_404(db, project_id)
    rows = await project_service.list_project_user_access(db, project_id)
    return [
        ProjectUserAccessDetailResponse(
            id=access.id,
            project_id=access.project_id,
            user_id=access.user_id,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            role=access.role,
            granted_at=access.granted_at,
        )
        for access, user in rows
    ]

@router.get(
    "/{project_id}/access/organizations",
    response_model=list[ProjectOrganizationAccessDetailResponse],
)
async def list_organization_access(
    project_id: str,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectOrganizationAccessDetailResponse]:
    await _assert_project_access(db, actor, project_id)
    await project_service.get_project_or_404(db, project_id)
    rows = await project_service.list_project_organization_access(db, project_id)
    return [
        ProjectOrganizationAccessDetailResponse(
            id=access.id,
            project_id=access.project_id,
            organization_id=access.organization_id,
            name=org.name,
            slug=org.slug,
            granted_at=access.granted_at,
        )
        for access, org in rows
    ]

@router.delete(
    "/{project_id}/access/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_user_access(
    project_id: str,
    user_id: str,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _assert_project_access(db, actor, project_id)
    await project_service.revoke_user_access(db, project_id, user_id)

@router.delete(
    "/{project_id}/access/organizations/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_organization_access(
    project_id: str,
    organization_id: str,
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _assert_project_access(db, actor, project_id)
    await project_service.revoke_organization_access(db, project_id, organization_id)

@router.get("/{project_id}/phases-with-deps")
async def list_project_phases_with_deps(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _assert_project_access(db, user, project_id)
    return await phase_service.list_project_phases_with_deps(db, project_id)

@router.get("/{project_id}/phases", response_model=list[ProjectPhaseResponse])
async def list_project_phases(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectPhaseResponse]:
    await _assert_project_access(db, user, project_id)
    details = await phase_service.list_project_phases_with_details(db, project_id)
    return [ProjectPhaseResponse(**d) for d in details]

@router.post(
    "/{project_id}/phases",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def attach_phase_to_project(
    project_id: str,
    payload: AttachPhaseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _assert_project_access(db, user, project_id)
    await phase_service.attach_phase_to_project(db, project_id, payload.phase_id)

@router.delete("/{project_id}/phases/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_phase_from_project(
    project_id: str,
    phase_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await _assert_project_access(db, user, project_id)
    await phase_service.detach_phase_from_project(db, project_id, phase_id)

@router.patch("/{project_id}/phases/{phase_id}", response_model=ProjectPhaseResponse)
async def update_project_phase_status(
    project_id: str,
    phase_id: str,
    payload: ProjectPhaseStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectPhaseResponse:
    await _assert_project_access(db, user, project_id)
    link = await phase_service.update_project_phase_status(db, project_id, phase_id, payload.status)
    phase = await phase_service.get_phase_or_404(db, phase_id)
    return ProjectPhaseResponse(
        id=link.id,
        phase_id=link.phase_id,
        phase_name=phase.name,
        phase_description=phase.description,
        status=link.status,
    )
