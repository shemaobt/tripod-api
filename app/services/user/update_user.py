from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.services.user.get_user_by_id import get_user_by_id


async def update_user(
    db: AsyncSession,
    user_id: str,
    is_active: bool | None = None,
    is_platform_admin: bool | None = None,
) -> User:
    user = await get_user_by_id(db, user_id)
    if is_active is not None:
        user.is_active = is_active
    if is_platform_admin is not None:
        user.is_platform_admin = is_platform_admin
    await db.flush()
    await db.refresh(user)
    return user
