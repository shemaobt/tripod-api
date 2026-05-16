from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.translation_helper import AgentId, THChat


async def create_chat(
    db: AsyncSession,
    user_id: str,
    *,
    agent_id: AgentId = AgentId.STORYTELLER,
    title: str | None = None,
) -> THChat:
    chat = THChat(user_id=user_id, agent_id=agent_id, title=title)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat
