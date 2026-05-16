from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.translation_helper import THChat, THChatMessage


async def list_chats_for_user(db: AsyncSession, user_id: str) -> list[dict[str, object]]:
    last_msg_sq = (
        select(
            THChatMessage.chat_id.label("chat_id"),
            func.max(THChatMessage.created_at).label("last_message_at"),
        )
        .group_by(THChatMessage.chat_id)
        .subquery()
    )
    stmt = (
        select(
            THChat.id,
            THChat.user_id,
            THChat.agent_id,
            THChat.title,
            THChat.created_at,
            THChat.updated_at,
            last_msg_sq.c.last_message_at,
        )
        .outerjoin(last_msg_sq, last_msg_sq.c.chat_id == THChat.id)
        .where(THChat.user_id == user_id)
        .order_by(desc(func.coalesce(last_msg_sq.c.last_message_at, THChat.created_at)))
    )
    result = await db.execute(stmt)
    return [dict(r) for r in result.mappings().all()]
