from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.translation_helper import THChatMessage


async def list_messages(
    db: AsyncSession,
    chat_id: str,
    *,
    limit: int | None = None,
) -> list[THChatMessage]:
    if limit is None:
        stmt = (
            select(THChatMessage)
            .where(THChatMessage.chat_id == chat_id)
            .order_by(THChatMessage.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    stmt = (
        select(THChatMessage)
        .where(THChatMessage.chat_id == chat_id)
        .order_by(THChatMessage.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(reversed(result.scalars().all()))
