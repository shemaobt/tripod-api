from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.services.user.get_user_by_id import get_user_by_id

_UNSET: object = object()


async def update_user(
    db: AsyncSession,
    user_id: str,
    is_active: bool | None = None,
    is_platform_admin: bool | None = None,
    avatar_url: str | None | object = _UNSET,
    display_name: str | None = None,
    locale: str | None = None,
) -> User:
    user = await get_user_by_id(db, user_id)
    if display_name is not None:
        user.display_name = display_name
    if is_active is not None:
        user.is_active = is_active
    if is_platform_admin is not None:
        user.is_platform_admin = is_platform_admin
    if avatar_url is not _UNSET:
        user.avatar_url = avatar_url or None  # type: ignore[assignment]
    if locale is not None:
        user.locale = locale
    await db.commit()
    await db.refresh(user)
    return user
