from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.auth import AccessRequest
from app.services.authorization.get_app_by_key import get_app_by_key


async def create_access_request(
    db: AsyncSession,
    user_id: str,
    app_key: str,
    note: str | None = None,
) -> AccessRequest:
    """Create an access request, or return existing pending/approved one."""
    app = await get_app_by_key(db, app_key)
    if not app:
        raise NotFoundError(f"App not found: {app_key}")

    # Return existing pending or approved request (idempotent)
    stmt: Select[tuple[AccessRequest]] = (
        select(AccessRequest)
        .where(
            AccessRequest.user_id == user_id,
            AccessRequest.app_id == app.id,
            AccessRequest.status.in_(["pending", "approved"]),
        )
        .order_by(AccessRequest.requested_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    request = AccessRequest(
        user_id=user_id,
        app_id=app.id,
        note=note,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request
