from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RoleError
from app.db.models.auth import User
from app.services.authorization.has_role import has_role


async def assert_can_manage_roles(db: AsyncSession, actor_user: User, app_key: str) -> None:

    if actor_user.is_platform_admin:
        return
    if await has_role(db, actor_user.id, app_key, "admin"):
        return
    raise RoleError("Actor cannot manage roles for this app")
