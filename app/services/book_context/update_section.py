from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.models.book_context import BCDStatus, BookContextDocument
from app.services.book_context.get_bcd import get_bcd_or_404
from app.services.i18n.back_translate_content import back_translate_content

EDITABLE_SECTIONS = frozenset(
    {
        "structural_outline",
        "participant_register",
        "discourse_threads",
        "theological_spine",
        "places",
        "objects",
        "institutions",
        "genre_context",
        "maintenance_notes",
    }
)


async def update_section(
    db: AsyncSession,
    bcd_id: str,
    section_key: str,
    data: Any,
    user_id: str,
    locale: str = "en",
) -> BookContextDocument:
    """Update a BCD section. Back-translates to English if locale is not 'en'."""
    bcd = await get_bcd_or_404(db, bcd_id)

    if bcd.status == BCDStatus.APPROVED:
        raise ConflictError(
            "Cannot edit an approved Book Context Document. Create a new version instead."
        )

    if bcd.status == BCDStatus.GENERATING:
        raise ConflictError("Cannot edit a document that is currently being generated.")

    if section_key not in EDITABLE_SECTIONS:
        raise NotFoundError(f"Unknown section: {section_key}")

    if not bcd.locked_by:
        raise ConflictError("You must lock the document before editing.")

    if bcd.locked_by != user_id:
        raise AuthorizationError("This document is locked by another user.")

    if locale and locale != "en" and isinstance(data, dict):
        data = await back_translate_content(data, locale)

    setattr(bcd, section_key, data)
    bcd.translations = None
    await db.commit()
    await db.refresh(bcd)
    return bcd
