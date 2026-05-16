from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.translation_helper import THChatMessage


async def list_messages(
    db: AsyncSession,
    chat_id: str,
    *,
    limit: int | None = None,
) -> list[THChatMessage]:
    stmt = (
        select(THChatMessage)
        .where(THChatMessage.chat_id == chat_id)
        .order_by(THChatMessage.created_at.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
