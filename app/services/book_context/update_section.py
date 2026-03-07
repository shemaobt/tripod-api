from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models.book_context import BCDStatus, BookContextDocument
from app.services.book_context.get_bcd import get_bcd_or_404

EDITABLE_SECTIONS = frozenset({
    "structural_outline",
    "participant_register",
    "discourse_threads",
    "theological_spine",
    "places",
    "objects",
    "institutions",
    "genre_context",
    "maintenance_notes",
})


async def update_section(
    db: AsyncSession,
    bcd_id: str,
    section_key: str,
    data: Any,
) -> BookContextDocument:
    bcd = await get_bcd_or_404(db, bcd_id)

    if bcd.status == BCDStatus.APPROVED:
        raise ConflictError("Cannot edit an approved Book Context Document. Create a new version instead.")

    if bcd.status == BCDStatus.GENERATING:
        raise ConflictError("Cannot edit a document that is currently being generated.")

    if section_key not in EDITABLE_SECTIONS:
        raise NotFoundError(f"Unknown section: {section_key}")

    setattr(bcd, section_key, data)
    await db.commit()
    await db.refresh(bcd)
    return bcd
