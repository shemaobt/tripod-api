from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenError
from app.db.models.auth import RefreshToken
from app.services.auth.get_user_by_id import get_user_by_id
from app.services.auth.hash_password import hash_password
from app.services.auth.validate_reset_token import validate_reset_token


async def reset_password_with_token(db: AsyncSession, raw_token: str, new_password: str) -> None:
    """Validate a reset token, update the user's password, and revoke all sessions."""
    token_record = await validate_reset_token(db, raw_token)

    user = await get_user_by_id(db, token_record.user_id)
    if not user:
        raise InvalidTokenError("Invalid or expired reset link.")

    user.password_hash = hash_password(new_password)
    token_record.used_at = datetime.now(UTC)

    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),  # type: ignore[arg-type]
        )
        .values(revoked_at=datetime.now(UTC))
    )

    await db.commit()
