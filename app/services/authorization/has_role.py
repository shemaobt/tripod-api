from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import UserAppRole
from app.services.authorization.get_app_by_key import get_app_by_key
from app.services.authorization.get_role import get_role


async def has_role(db: AsyncSession, user_id: str, app_key: str, role_key: str) -> bool:

    app = await get_app_by_key(db, app_key)
    if not app:
        return False

    role = await get_role(db, app.id, role_key)
    if not role:
        return False

    stmt: Select[tuple[UserAppRole]] = select(UserAppRole).where(
        UserAppRole.user_id == user_id,
        UserAppRole.app_id == app.id,
        UserAppRole.role_id == role.id,
        UserAppRole.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
