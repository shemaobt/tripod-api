from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.language import Language
from app.services.common import get_or_raise


async def get_language_or_404(db: AsyncSession, language_id: str) -> Language:
    return await get_or_raise(db, Language, language_id, label="Language")
