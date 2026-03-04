from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification


async def unread_count(db: AsyncSession, user_id: str, app_id: str) -> int:
    """Return the number of unread notifications for a user within an app."""
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.app_id == app_id,
            Notification.is_read.is_(False),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()
