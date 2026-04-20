from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.models.auth import User
from app.db.models.org import OrganizationMember
from app.db.models.project import ProjectOrganizationAccess, ProjectUserAccess


async def require_project_access(db: AsyncSession, project_id: str, user: User) -> None:
    """Raise AuthorizationError unless the user can access the project.

    Access is granted to platform admins, direct project members, or members
    of an organization with access to the project.
    """
    if user.is_platform_admin:
        return

    user_org_ids = select(OrganizationMember.organization_id).where(
        OrganizationMember.user_id == user.id
    )
    direct = (
        select(ProjectUserAccess.id)
        .where(
            ProjectUserAccess.project_id == project_id,
            ProjectUserAccess.user_id == user.id,
        )
        .exists()
    )
    via_org = (
        select(ProjectOrganizationAccess.id)
        .where(
            ProjectOrganizationAccess.project_id == project_id,
            ProjectOrganizationAccess.organization_id.in_(user_org_ids),
        )
        .exists()
    )

    stmt = select(1).where(or_(direct, via_org))
    result = await db.execute(stmt)
    if result.scalar() is None:
        raise AuthorizationError("You do not have access to this project")
