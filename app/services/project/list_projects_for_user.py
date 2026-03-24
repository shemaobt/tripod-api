from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.core.org_scope import get_managed_org_ids
from app.db.models.auth import User
from app.db.models.project import Project, ProjectOrganizationAccess
from app.services.project.list_all_projects import list_all_projects
from app.services.project.list_projects_accessible_to_user import (
    list_projects_accessible_to_user,
)
from app.services.project.list_projects_by_organization import (
    list_projects_by_organization,
)


async def list_projects_for_user(
    db: AsyncSession,
    user: User,
    organization_id: str | None = None,
    language_id: str | None = None,
) -> list[Project]:
    """Return projects visible to a user, applying org/role scoping rules."""
    if user.is_platform_admin:
        if organization_id:
            projects = await list_projects_by_organization(db, organization_id)
        else:
            projects = await list_all_projects(db)
    else:
        managed_org_ids = await get_managed_org_ids(db, user.id)
        if organization_id:
            if organization_id not in managed_org_ids:
                raise AuthorizationError("You do not have access to the requested organization.")
            projects = await list_projects_by_organization(db, organization_id)
        elif managed_org_ids:
            projects = await _list_projects_by_organizations(db, managed_org_ids)
        else:
            projects = await list_projects_accessible_to_user(db, user.id)

    if language_id is not None:
        projects = [p for p in projects if p.language_id == language_id]

    return projects


async def _list_projects_by_organizations(
    db: AsyncSession,
    organization_ids: list[str],
) -> list[Project]:
    """Fetch projects linked to any of the given organizations in a single query."""
    org_project_ids = select(ProjectOrganizationAccess.project_id).where(
        ProjectOrganizationAccess.organization_id.in_(organization_ids)
    )
    stmt = select(Project).where(Project.id.in_(org_project_ids)).order_by(Project.name)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
