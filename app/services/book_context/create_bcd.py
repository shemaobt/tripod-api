from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.models.book_context import BCDStatus, BookContextDocument
from app.db.models.meaning_map import BibleBook


async def create_bcd(
    db: AsyncSession,
    book_id: str,
    user_id: str,
    genre: str,
    *,
    section_label: str | None = None,
    section_range_start: int | None = None,
    section_range_end: int | None = None,
) -> BookContextDocument:
    result = await db.execute(select(BibleBook).where(BibleBook.id == book_id))
    book = result.scalar_one_or_none()
    if not book or book.testament.value != "OT":
        raise AuthorizationError(
            "Book Context Documents can only be created for Old Testament books."
        )

    max_version = 0
    existing = await db.execute(
        select(BookContextDocument.version)
        .where(
            BookContextDocument.book_id == book_id,
            BookContextDocument.section_range_start == section_range_start,
            BookContextDocument.section_range_end == section_range_end,
        )
        .order_by(BookContextDocument.version.desc())
        .limit(1)
    )
    row = existing.scalar_one_or_none()
    if row:
        max_version = row

    bcd = BookContextDocument(
        book_id=book_id,
        prepared_by=user_id,
        status=BCDStatus.DRAFT,
        version=max_version + 1,
        section_label=section_label,
        section_range_start=section_range_start,
        section_range_end=section_range_end,
        genre_context={"primary_genre": genre},
    )
    db.add(bcd)
    await db.commit()
    await db.refresh(bcd)
    return bcd
