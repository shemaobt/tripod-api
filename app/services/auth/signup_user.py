from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.auth import User
from app.models.auth import UserSignupRequest
from app.services.auth.get_user_by_email import get_user_by_email
from app.services.auth.hash_password import hash_password

async def signup_user(db: AsyncSession, payload: UserSignupRequest) -> User:

    existing_user = await get_user_by_email(db, payload.email)
    if existing_user:
        raise ConflictError("Email already exists")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
