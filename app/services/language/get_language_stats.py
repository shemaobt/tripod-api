from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import Project
from app.services.language.get_language_or_404 import get_language_or_404


async def get_language_stats(db: AsyncSession, language_id: str) -> int:
    """Return how many projects use a language, raising 404 if it is unknown."""
    await get_language_or_404(db, language_id)
    stmt = select(func.count()).select_from(Project).where(Project.language_id == language_id)
    result = await db.execute(stmt)
    return result.scalar_one()
