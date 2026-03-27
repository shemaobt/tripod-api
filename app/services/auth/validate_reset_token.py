from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenError
from app.db.models.auth import PasswordResetToken
from app.services.auth.hash_refresh_token import hash_refresh_token


async def validate_reset_token(db: AsyncSession, raw_token: str) -> PasswordResetToken:
    """Validate a password reset token and return the record.

    Raises InvalidTokenError if the token is invalid, expired, or already used.
    """
    token_hash = hash_refresh_token(raw_token)

    stmt = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > datetime.now(UTC),
    )
    result = await db.execute(stmt)
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise InvalidTokenError("Invalid or expired reset link. Please request a new one.")

    return token_record
