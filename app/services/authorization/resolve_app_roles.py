from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.services.authorization.list_roles import list_roles


async def resolve_user_app_role(db: AsyncSession, user: User, app_key: str) -> str:
    """Return the highest-priority role for a user within an app."""
    if user.is_platform_admin:
        return "admin"
    roles = await list_roles(db, user.id, app_key)
    role_keys = [r[1] for r in roles]
    if "admin" in role_keys:
        return "admin"
    if "analyst" in role_keys:
        return "analyst"
    return "viewer"


async def resolve_user_app_roles(db: AsyncSession, user: User, app_key: str) -> list[str]:
    """Return all role keys for a user within an app."""
    if user.is_platform_admin:
        return ["admin"]
    roles = await list_roles(db, user.id, app_key)
    return [r[1] for r in roles] or ["viewer"]
