from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.org import OrganizationMember
from app.db.models.project import ProjectOrganizationAccess, ProjectUserAccess

async def can_access_project(
    db: AsyncSession,
    user_id: str,
    project_id: str,
) -> bool:

    direct = await db.execute(
        select(ProjectUserAccess.id)
        .where(
            ProjectUserAccess.project_id == project_id,
            ProjectUserAccess.user_id == user_id,
        )
        .limit(1)
    )
    if direct.scalar_one_or_none():
        return True

    org_access = await db.execute(
        select(ProjectOrganizationAccess.id)
        .join(
            OrganizationMember,
            and_(
                OrganizationMember.organization_id == ProjectOrganizationAccess.organization_id,
                OrganizationMember.user_id == user_id,
            ),
        )
        .where(ProjectOrganizationAccess.project_id == project_id)
        .limit(1)
    )
    return org_access.scalar_one_or_none() is not None
