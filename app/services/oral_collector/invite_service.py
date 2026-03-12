from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.models.auth import User
from app.db.models.project import ProjectInvite, ProjectUserAccess


async def create_invite(
    db: AsyncSession,
    project_id: str,
    email: str,
    role: str,
    invited_by: str,
) -> ProjectInvite:
    """Create a project invite for an existing user.

    Raises NotFoundError if no active user with that email exists.
    Raises ConflictError if a pending invite already exists.
    """
    # Verify the email belongs to an existing active user
    user_stmt = select(User).where(User.email == email, User.is_active.is_(True))
    user_result = await db.execute(user_stmt)
    if user_result.scalar_one_or_none() is None:
        raise NotFoundError("No registered user found with that email")

    # Check for duplicate pending invite
    stmt = select(ProjectInvite).where(
        ProjectInvite.project_id == project_id,
        ProjectInvite.email == email,
        ProjectInvite.status == "pending",
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError("A pending invite already exists for this email")

    invite = ProjectInvite(
        project_id=project_id,
        email=email,
        role=role,
        invited_by=invited_by,
        app_key="oral-collector",
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite


async def list_user_invites(db: AsyncSession, user_email: str) -> list[ProjectInvite]:
    """List all pending invites for a user by email."""
    stmt = (
        select(ProjectInvite)
        .where(
            ProjectInvite.email == user_email,
            ProjectInvite.status == "pending",
        )
        .order_by(ProjectInvite.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def accept_invite(
    db: AsyncSession, invite_id: str, user_id: str, user_email: str
) -> ProjectInvite:
    """Accept an invite. Creates ProjectUserAccess entry with the invite's role."""
    invite = await _get_invite_for_user(db, invite_id, user_email)

    member = ProjectUserAccess(
        project_id=invite.project_id,
        user_id=user_id,
        role=invite.role,
        invited_by=invite.invited_by,
    )
    db.add(member)

    invite.status = "accepted"
    invite.accepted_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(invite)
    return invite


async def decline_invite(db: AsyncSession, invite_id: str, user_email: str) -> ProjectInvite:
    """Decline an invite."""
    invite = await _get_invite_for_user(db, invite_id, user_email)

    invite.status = "declined"
    await db.commit()
    await db.refresh(invite)
    return invite


async def _get_invite_for_user(db: AsyncSession, invite_id: str, user_email: str) -> ProjectInvite:
    """Fetch a pending invite and verify it belongs to the user."""
    stmt = select(ProjectInvite).where(ProjectInvite.id == invite_id)
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()
    if not invite:
        raise NotFoundError("Invite not found")
    if invite.email != user_email:
        raise AuthorizationError("This invite does not belong to you")
    if invite.status != "pending":
        raise ConflictError(f"Invite has already been {invite.status}")
    return invite
