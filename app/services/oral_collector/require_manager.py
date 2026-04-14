from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.models.project import ProjectUserAccess


async def require_project_manager(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    *,
    action: str = "perform this action",
    is_platform_admin: bool = False,
) -> None:
    """Raise AuthorizationError unless the user is a project manager or a platform admin."""
    if is_platform_admin:
        return
    stmt = select(ProjectUserAccess).where(
        ProjectUserAccess.project_id == project_id,
        ProjectUserAccess.user_id == user_id,
        ProjectUserAccess.role == "manager",
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise AuthorizationError(f"Only project managers can {action}")
