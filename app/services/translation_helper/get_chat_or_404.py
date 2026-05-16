from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.models.translation_helper import THChat
from app.services.common import get_or_raise


async def get_chat_or_404(
    db: AsyncSession, chat_id: str, *, user_id: str | None = None
) -> THChat:
    chat = await get_or_raise(db, THChat, chat_id, label="Chat")
    if user_id is not None and chat.user_id != user_id:
        raise AuthorizationError("You do not have access to this chat")
    return chat
