from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.oc_project import OCProjectInviteCreate, OCProjectInviteResponse
from app.services.oral_collector import invite_service
from app.services.oral_collector.require_manager import require_project_manager

invites_router = APIRouter()


async def _require_manager(project_id: str, user: User, db: AsyncSession) -> None:

    if user.is_platform_admin:
        return
    await require_project_manager(db, project_id, user.id, action="manage invites")


@invites_router.post(
    "/projects/{project_id}/invites",
    response_model=OCProjectInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    project_id: str,
    payload: OCProjectInviteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OCProjectInviteResponse:

    await _require_manager(project_id, user, db)
    invite = await invite_service.create_invite(
        db, project_id, payload.email, payload.role, user.id
    )
    return OCProjectInviteResponse.model_validate(invite)


@invites_router.get(
    "/invites/mine",
    response_model=list[OCProjectInviteResponse],
)
async def list_my_invites(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OCProjectInviteResponse]:

    rows = await invite_service.list_user_invites(db, user.email)
    return [
        OCProjectInviteResponse(
            id=invite.id,
            project_id=invite.project_id,
            project_name=project_name,
            email=invite.email,
            invited_by=invite.invited_by,
            status=invite.status,
            role=invite.role,
            app_key=invite.app_key,
            created_at=invite.created_at,
            accepted_at=invite.accepted_at,
        )
        for invite, project_name in rows
    ]


@invites_router.post(
    "/invites/{invite_id}/accept",
    response_model=OCProjectInviteResponse,
)
async def accept_invite(
    invite_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OCProjectInviteResponse:

    invite = await invite_service.accept_invite(db, invite_id, user.id, user.email)
    return OCProjectInviteResponse.model_validate(invite)


@invites_router.post(
    "/invites/{invite_id}/decline",
    response_model=OCProjectInviteResponse,
)
async def decline_invite(
    invite_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OCProjectInviteResponse:

    invite = await invite_service.decline_invite(db, invite_id, user.email)
    return OCProjectInviteResponse.model_validate(invite)
