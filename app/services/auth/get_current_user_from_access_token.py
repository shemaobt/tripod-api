from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cache import get_cached_user, set_cached_user
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.models.auth import User
from app.services.auth.get_user_by_id import get_user_by_id
from app.utils.jwt import decode_token


async def get_current_user_from_access_token(db: AsyncSession, token: str) -> User:
    """Resolve current user from access token, using in-memory cache."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")

    user_id = payload["sub"]

    user = get_cached_user(user_id)
    if user is None:
        user = await get_user_by_id(db, user_id)
        if not user:
            raise AuthenticationError("User not found")
        set_cached_user(user_id, user)

    if not user.is_active:
        raise AuthorizationError("Inactive user")
    return user
