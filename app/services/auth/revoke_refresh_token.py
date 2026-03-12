from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import RefreshToken
from app.services.auth.hash_refresh_token import hash_refresh_token

async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> None:

    token_hash = hash_refresh_token(refresh_token)
    stmt: Select[tuple[RefreshToken]] = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    token_record = result.scalar_one_or_none()
    if token_record:
        token_record.revoked_at = datetime.now(UTC)
        await db.commit()
