from __future__ import annotations

import copy
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.exceptions import NotFoundError
from app.db.models.book_context import BookContextDocument
from app.services.i18n.translate_content import translate_document_content

logger = logging.getLogger(__name__)

TRANSLATABLE_SECTIONS = [
    "structural_outline",
    "participant_register",
    "discourse_threads",
    "theological_spine",
    "places",
    "objects",
    "institutions",
    "genre_context",
]


async def translate_bcd(
    db: AsyncSession,
    bcd_id: str,
    language: str,
) -> dict:
    """Translate a BCD's content sections to the target language, with caching."""
    result = await db.execute(select(BookContextDocument).where(BookContextDocument.id == bcd_id))
    bcd = result.scalar_one_or_none()
    if not bcd:
        raise NotFoundError(f"Book context document {bcd_id} not found")

    existing: dict = bcd.translations or {}
    if language in existing:
        return dict(existing[language])

    sections_to_translate: dict = {}
    for key in TRANSLATABLE_SECTIONS:
        value = getattr(bcd, key, None)
        if value is not None:
            sections_to_translate[key] = value

    translated = await translate_document_content(sections_to_translate, language)

    updated = copy.deepcopy(existing)
    updated[language] = translated
    bcd.translations = updated
    flag_modified(bcd, "translations")
    await db.commit()
    await db.refresh(bcd)

    return translated
