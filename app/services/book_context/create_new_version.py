from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.db.models.book_context import BCDStatus, BookContextDocument
from app.services.book_context.get_bcd import get_bcd_or_404


async def create_new_version(
    db: AsyncSession,
    bcd_id: str,
    user_id: str,
) -> BookContextDocument:
    source = await get_bcd_or_404(db, bcd_id)

    if source.status != BCDStatus.APPROVED:
        raise ConflictError("Can only create a new version from an approved document.")

    new_bcd = BookContextDocument(
        book_id=source.book_id,
        prepared_by=user_id,
        status=BCDStatus.DRAFT,
        version=source.version + 1,
        section_label=source.section_label,
        section_range_start=source.section_range_start,
        section_range_end=source.section_range_end,
        structural_outline=source.structural_outline,
        participant_register=source.participant_register,
        discourse_threads=source.discourse_threads,
        theological_spine=source.theological_spine,
        places=source.places,
        objects=source.objects,
        institutions=source.institutions,
        genre_context=source.genre_context,
        maintenance_notes=source.maintenance_notes,
    )
    db.add(new_bcd)
    await db.commit()
    await db.refresh(new_bcd)
    return new_bcd
