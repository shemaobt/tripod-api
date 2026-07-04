from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.language import Language
from app.services.language.get_language_or_404 import get_language_or_404


async def deactivate_language(db: AsyncSession, language_id: str) -> Language:
    """Soft-delete a language by marking it inactive, preserving its rows."""
    language = await get_language_or_404(db, language_id)
    language.is_active = False
    await db.commit()
    await db.refresh(language)
    return language
