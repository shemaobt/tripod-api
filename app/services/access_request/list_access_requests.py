from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import AccessRequest, App

async def list_access_requests(
    db: AsyncSession,
    app_key: str | None = None,
    status: str | None = None,
) -> list[tuple[AccessRequest, str]]:

    stmt: Select[tuple[AccessRequest, str]] = select(AccessRequest, App.app_key).join(
        App, AccessRequest.app_id == App.id
    )

    if app_key:
        stmt = stmt.where(App.app_key == app_key)
    if status:
        stmt = stmt.where(AccessRequest.status == status)

    stmt = stmt.order_by(AccessRequest.requested_at.desc())
    result = await db.execute(stmt)
    return list(result.all())
