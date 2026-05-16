from sqlalchemy.ext.asyncio import AsyncSession

from app.services.translation_helper.get_chat_or_404 import get_chat_or_404


async def delete_chat(db: AsyncSession, chat_id: str, user_id: str) -> None:
    chat = await get_chat_or_404(db, chat_id, user_id=user_id)
    await db.delete(chat)
    await db.commit()
