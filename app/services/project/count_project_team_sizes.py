from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import ProjectUserAccess


async def count_project_team_sizes(db: AsyncSession, project_ids: list[str]) -> dict[str, int]:
    """Map each project id to its count of distinct users with direct access.

    Runs a single grouped query to avoid N+1 lookups; ids with no access rows
    resolve to 0.
    """
    if not project_ids:
        return {}
    stmt = (
        select(
            ProjectUserAccess.project_id,
            func.count(distinct(ProjectUserAccess.user_id)),
        )
        .where(ProjectUserAccess.project_id.in_(project_ids))
        .group_by(ProjectUserAccess.project_id)
    )
    result = await db.execute(stmt)
    counts = dict(result.all())
    return {project_id: counts.get(project_id, 0) for project_id in project_ids}
