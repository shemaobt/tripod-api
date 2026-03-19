from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import Project, ProjectOrganizationAccess


async def list_projects_by_organization(
    db: AsyncSession,
    organization_id: str,
) -> list[Project]:
    org_project_ids = select(ProjectOrganizationAccess.project_id).where(
        ProjectOrganizationAccess.organization_id == organization_id
    )
    stmt = (
        select(Project)
        .where(Project.id.in_(org_project_ids))
        .order_by(Project.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
