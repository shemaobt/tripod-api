from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.db.models.sound_necklace import SnSession
from app.services.project.list_projects_accessible_to_user import (
    list_projects_accessible_to_user,
)


async def list_sessions(db: AsyncSession, user: User) -> list[SnSession]:
    """The user's sessions across every project they can reach, most recent first.

    Reach is the same union the rest of the platform uses: direct project grants
    plus the projects reachable through the user's organizations.
    """
    stmt = select(SnSession).order_by(SnSession.updated_at.desc())
    if not user.is_platform_admin:
        projects = await list_projects_accessible_to_user(db, user.id)
        stmt = stmt.where(SnSession.project_id.in_([p.id for p in projects]))
    result = await db.execute(stmt)
    return list(result.scalars().all())
