from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.org import Organization
from app.db.models.project import ProjectOrganizationAccess


async def list_project_organization_access(
    db: AsyncSession,
    project_id: str,
) -> list[tuple[ProjectOrganizationAccess, Organization]]:
    stmt: Select[tuple[ProjectOrganizationAccess, Organization]] = (
        select(ProjectOrganizationAccess, Organization)
        .join(Organization, ProjectOrganizationAccess.organization_id == Organization.id)
        .where(ProjectOrganizationAccess.project_id == project_id)
        .order_by(ProjectOrganizationAccess.granted_at)
    )
    result = await db.execute(stmt)
    return [row._tuple() for row in result.all()]
