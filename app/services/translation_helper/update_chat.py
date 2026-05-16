from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.translation_helper import AgentId, THChat
from app.services.translation_helper.get_chat_or_404 import get_chat_or_404


async def update_chat(
    db: AsyncSession,
    chat_id: str,
    user_id: str,
    *,
    title: str | None = None,
    agent_id: AgentId | None = None,
) -> THChat:
    chat = await get_chat_or_404(db, chat_id, user_id=user_id)
    if title is not None:
        chat.title = title
    if agent_id is not None:
        chat.agent_id = agent_id
    await db.commit()
    await db.refresh(chat)
    return chat
