from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User, UserAppRole
from app.services.authorization.assert_can_manage_roles import assert_can_manage_roles
from app.services.authorization.grant_app_role import grant_app_role


async def assign_role(
    db: AsyncSession,
    actor_user: User,
    target_user_id: str,
    app_key: str,
    role_key: str,
) -> UserAppRole:
    await assert_can_manage_roles(db, actor_user, app_key)
    return await grant_app_role(db, target_user_id, app_key, role_key, granted_by=actor_user.id)
