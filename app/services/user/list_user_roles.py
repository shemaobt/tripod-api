from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import App, Role, UserAppRole


async def list_user_roles(db: AsyncSession, user_id: str) -> list[tuple[str, str, datetime]]:
    stmt = (
        select(App.app_key, Role.role_key, UserAppRole.granted_at)
        .join(Role, Role.app_id == App.id)
        .join(
            UserAppRole,
            and_(UserAppRole.role_id == Role.id, UserAppRole.app_id == App.id),
        )
        .where(UserAppRole.user_id == user_id, UserAppRole.revoked_at.is_(None))
        .order_by(App.app_key, Role.role_key)
    )
    result = await db.execute(stmt)
    return [(row[0], row[1], row[2]) for row in result.all()]
