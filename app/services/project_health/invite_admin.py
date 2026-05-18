from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.auth import User
from app.models.project_health import AdminInviteResponse
from app.services.authorization.grant_app_role import grant_app_role

PH_APP_KEY = "project-health"
PH_ADMIN_ROLE = "admin"


async def invite_admin(
    db: AsyncSession, *, email: str, invited_by_user_id: str
) -> AdminInviteResponse:
    """Grant the project-health admin role to an existing user identified by
    email. Raises NotFoundError if no user with that email exists yet — the
    invitee must sign up first, then be invited again."""
    stmt = select(User).where(User.email == email.lower())
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise NotFoundError(
            "No user with that email has signed up yet. Ask them to sign up at "
            "the project-health login page first, then invite them again."
        )

    assignment = await grant_app_role(
        db,
        user.id,
        PH_APP_KEY,
        PH_ADMIN_ROLE,
        granted_by=invited_by_user_id,
    )
    return AdminInviteResponse(
        email=user.email,
        pre_approved_role=PH_ADMIN_ROLE,
        access_request_id=assignment.id,
        granted=True,
    )
