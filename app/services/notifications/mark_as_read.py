from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.notification import Notification


async def mark_as_read(db: AsyncSession, notification_id: str, user_id: str) -> Notification:
    """Mark a single notification as read."""
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    result = await db.execute(stmt)
    notif = result.scalar_one_or_none()
    if notif is None:
        raise NotFoundError(f"Notification {notification_id} not found")
    notif.is_read = True
    await db.commit()
    await db.refresh(notif)
    return notif
