from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.org import OrganizationMember
from app.db.models.project import Project, ProjectOrganizationAccess
from app.models.org import OrganizationStatsResponse


async def get_organization_stats(
    db: AsyncSession, organization_id: str
) -> OrganizationStatsResponse:
    project_count_q = select(func.count()).where(
        ProjectOrganizationAccess.organization_id == organization_id
    )
    member_count_q = select(func.count()).where(
        OrganizationMember.organization_id == organization_id
    )
    language_count_q = (
        select(func.count(func.distinct(Project.language_id)))
        .select_from(ProjectOrganizationAccess)
        .join(Project, ProjectOrganizationAccess.project_id == Project.id)
        .where(ProjectOrganizationAccess.organization_id == organization_id)
    )

    project_count = (await db.execute(project_count_q)).scalar() or 0
    member_count = (await db.execute(member_count_q)).scalar() or 0
    language_count = (await db.execute(language_count_q)).scalar() or 0

    return OrganizationStatsResponse(
        project_count=project_count,
        member_count=member_count,
        language_count=language_count,
    )
