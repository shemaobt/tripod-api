from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.auth import RefreshToken, User
from app.services.auth.hash_refresh_token import hash_refresh_token
from app.utils.jwt import create_token

settings = get_settings()


async def issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:

    access_token = create_token(user.id, "access", settings.access_token_expire_minutes)
    refresh_token = create_token(user.id, "refresh", settings.refresh_token_expire_minutes)

    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(minutes=settings.refresh_token_expire_minutes),
    )
    db.add(token_record)
    await db.commit()

    return access_token, refresh_token
