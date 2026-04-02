from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project import ProjectUserAccess


async def grant_user_access(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    role: str = "member",
) -> ProjectUserAccess:
    existing: Select[tuple[ProjectUserAccess]] = select(ProjectUserAccess).where(
        ProjectUserAccess.project_id == project_id,
        ProjectUserAccess.user_id == user_id,
    )
    result = await db.execute(existing)
    existing_access = result.scalar_one_or_none()
    if existing_access:
        return existing_access
    access = ProjectUserAccess(project_id=project_id, user_id=user_id, role=role)
    db.add(access)
    await db.commit()
    await db.refresh(access)
    return access
