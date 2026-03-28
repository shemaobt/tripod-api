from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.models.meaning_map import MeaningMap
from app.services.i18n.back_translate_content import back_translate_content


async def update_meaning_map_data(
    db: AsyncSession,
    mm: MeaningMap,
    data: dict[str, Any],
    user_id: str,
    locale: str = "en",
) -> MeaningMap:
    """Update meaning map data. Back-translates to English if locale is not 'en'."""
    if mm.locked_by and mm.locked_by != user_id:
        raise AuthorizationError("This meaning map is locked by another user")
    if mm.status == "approved":
        raise AuthorizationError("Cannot edit an approved meaning map")

    if locale and locale != "en":
        data = await back_translate_content(data, locale)

    mm.data = data
    mm.translations = None
    await db.commit()
    await db.refresh(mm)
    return mm
