from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cache import get_cached_user, set_cached_user
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.models.auth import User
from app.services.auth.get_user_by_id import get_user_by_id
from app.utils.jwt import decode_token


async def get_current_user_from_access_token(db: AsyncSession, token: str) -> User:

    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    user_id = payload["sub"]

    cached = get_cached_user(user_id)
    if cached is not None:
        user: User = cached
    else:
        found = await get_user_by_id(db, user_id)
        if not found:
            raise AuthenticationError("User not found")
        set_cached_user(user_id, found)
        user = found

    if not user.is_active:
        raise AuthorizationError("Inactive user")
    return user
