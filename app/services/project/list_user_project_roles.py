from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import ProjectUserAccess


async def list_user_project_roles(db: AsyncSession, user_id: str) -> dict[str, str]:

    stmt = select(ProjectUserAccess.project_id, ProjectUserAccess.role).where(
        ProjectUserAccess.user_id == user_id
    )
    result = await db.execute(stmt)
    return {row.project_id: row.role for row in result.all()}
