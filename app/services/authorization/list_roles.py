from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App, Role, UserAppRole

async def list_roles(
    db: AsyncSession, user_id: str, app_key: str | None = None
) -> list[tuple[str, str]]:

    stmt = (
        select(App.app_key, Role.role_key)
        .join(Role, Role.app_id == App.id)
        .join(
            UserAppRole,
            and_(UserAppRole.role_id == Role.id, UserAppRole.app_id == App.id),
        )
        .where(UserAppRole.user_id == user_id, UserAppRole.revoked_at.is_(None))
    )
    if app_key:
        stmt = stmt.where(App.app_key == app_key)
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]
