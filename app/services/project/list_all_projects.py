from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import Project


async def list_all_projects(db: AsyncSession) -> list[Project]:
    """List all projects ordered by name (admin use)."""
    result = await db.execute(select(Project).order_by(Project.name))
    return list(result.scalars().unique().all())
