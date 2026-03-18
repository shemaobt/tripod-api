from __future__ import annotations

import copy
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.exceptions import NotFoundError
from app.db.models.meaning_map import MeaningMap
from app.services.i18n.translate_content import translate_document_content

logger = logging.getLogger(__name__)


async def translate_meaning_map(
    db: AsyncSession,
    meaning_map_id: str,
    language: str,
) -> dict:
    """Translate a meaning map's data to the target language, with caching."""
    result = await db.execute(select(MeaningMap).where(MeaningMap.id == meaning_map_id))
    mm = result.scalar_one_or_none()
    if not mm:
        raise NotFoundError(f"Meaning map {meaning_map_id} not found")

    existing: dict = mm.translations or {}
    if language in existing:
        return dict(existing[language])

    translated = await translate_document_content(mm.data, language)

    updated = copy.deepcopy(existing)
    updated[language] = translated
    mm.translations = updated
    flag_modified(mm, "translations")
    await db.commit()
    await db.refresh(mm)

    return translated
