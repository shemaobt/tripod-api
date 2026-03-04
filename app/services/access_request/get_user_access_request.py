from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.auth import AccessRequest
from app.services.authorization.get_app_by_key import get_app_by_key


async def get_user_access_request(
    db: AsyncSession,
    user_id: str,
    app_key: str,
) -> AccessRequest | None:
    """Return the most recent access request for a user+app."""
    app = await get_app_by_key(db, app_key)
    if not app:
        raise NotFoundError(f"App not found: {app_key}")

    stmt: Select[tuple[AccessRequest]] = (
        select(AccessRequest)
        .where(
            AccessRequest.user_id == user_id,
            AccessRequest.app_id == app.id,
        )
        .order_by(AccessRequest.requested_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
