from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.models.oc_project_user import OC_ProjectInvite, OC_ProjectUser


async def create_invite(
    db: AsyncSession,
    project_id: str,
    email: str,
    role: str,
    invited_by: str,
) -> OC_ProjectInvite:
    """Create a project invite. Raises ConflictError if a pending invite already exists."""
    # Check for existing pending invite for same email + project
    stmt = select(OC_ProjectInvite).where(
        OC_ProjectInvite.project_id == project_id,
        OC_ProjectInvite.email == email,
        OC_ProjectInvite.status == "pending",
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError("A pending invite already exists for this email")

    invite = OC_ProjectInvite(
        project_id=project_id,
        email=email,
        role=role,
        invited_by=invited_by,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


async def list_user_invites(
    db: AsyncSession, user_email: str
) -> list[OC_ProjectInvite]:
    """List all pending invites for a user by email."""
    stmt = (
        select(OC_ProjectInvite)
        .where(
            OC_ProjectInvite.email == user_email,
            OC_ProjectInvite.status == "pending",
        )
        .order_by(OC_ProjectInvite.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def accept_invite(
    db: AsyncSession, invite_id: str, user_id: str, user_email: str
) -> OC_ProjectInvite:
    """Accept an invite. Creates OC_ProjectUser entry with the invite's role."""
    invite = await _get_invite_for_user(db, invite_id, user_email)

    # Create project membership with the role from the invite
    member = OC_ProjectUser(
        project_id=invite.project_id,
        user_id=user_id,
        role=invite.role,
        invited_by=invite.invited_by,
    )
    db.add(member)

    invite.status = "accepted"
    invite.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(invite)
    return invite


async def decline_invite(
    db: AsyncSession, invite_id: str, user_email: str
) -> OC_ProjectInvite:
    """Decline an invite."""
    invite = await _get_invite_for_user(db, invite_id, user_email)

    invite.status = "declined"
    await db.commit()
    await db.refresh(invite)
    return invite


async def _get_invite_for_user(
    db: AsyncSession, invite_id: str, user_email: str
) -> OC_ProjectInvite:
    """Fetch a pending invite and verify it belongs to the user."""
    stmt = select(OC_ProjectInvite).where(OC_ProjectInvite.id == invite_id)
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()
    if not invite:
        raise NotFoundError("Invite not found")
    if invite.email != user_email:
        raise AuthorizationError("This invite does not belong to you")
    if invite.status != "pending":
        raise ConflictError(f"Invite has already been {invite.status}")
    return invite
