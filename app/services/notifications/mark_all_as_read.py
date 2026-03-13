from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification


async def mark_all_as_read(db: AsyncSession, user_id: str) -> int:

    stmt = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount
