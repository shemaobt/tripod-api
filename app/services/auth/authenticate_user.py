from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.models.auth import User
from app.services.auth.get_user_by_email import get_user_by_email
from app.services.auth.verify_password import verify_password

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:

    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid credentials")
    if not user.is_active:
        raise AuthorizationError("Inactive user")
    return user
