from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError
from app.db.models.auth import User
from app.db.models.project import ProjectUserAccess
from app.models.oc_project import OCProjectInviteCreate, OCProjectInviteResponse
from app.services.oral_collector import invite_service

invites_router = APIRouter()


async def _require_manager(project_id: str, user: User, db: AsyncSession) -> None:
    """Verify the user is a manager for the given project (or platform admin)."""
    if user.is_platform_admin:
        return
    stmt = select(ProjectUserAccess).where(
        ProjectUserAccess.project_id == project_id,
        ProjectUserAccess.user_id == user.id,
        ProjectUserAccess.role == "manager",
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise AuthorizationError("Only project managers can manage invites")


# ---------------------------------------------------------------------------
# Invite endpoints
# ---------------------------------------------------------------------------


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
    """Create a project invite (manager only)."""
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
    """List pending invites for the current user."""
    invites = await invite_service.list_user_invites(db, user.email)
    return [OCProjectInviteResponse.model_validate(i) for i in invites]


@invites_router.post(
    "/invites/{invite_id}/accept",
    response_model=OCProjectInviteResponse,
)
async def accept_invite(
    invite_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OCProjectInviteResponse:
    """Accept a project invite."""
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
    """Decline a project invite."""
    invite = await invite_service.decline_invite(db, invite_id, user.email)
    return OCProjectInviteResponse.model_validate(invite)
