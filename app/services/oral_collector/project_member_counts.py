from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import ProjectUserAccess


async def get_member_counts(db: AsyncSession, project_ids: list[str]) -> dict[str, int]:
    """Return {project_id: member_count} for the given projects."""
    if not project_ids:
        return {}
    stmt = (
        select(
            ProjectUserAccess.project_id,
            func.count().label("member_count"),
        )
        .where(ProjectUserAccess.project_id.in_(project_ids))
        .group_by(ProjectUserAccess.project_id)
    )
    result = await db.execute(stmt)
    return {row.project_id: row.member_count for row in result.all()}
