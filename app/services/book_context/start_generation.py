from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.book_context import BCDStatus, BookContextDocument
from app.db.models.meaning_map import BibleBook
from app.services.book_context.get_bcd import get_bcd_or_404


@dataclass
class GenerationTarget:
    target_bcd: BookContextDocument
    book_name: str
    genre: str
    chapter_count: int
    user_feedback: str | None = None


class GenerationAlreadyInProgress(Exception):
    pass


async def start_generation(
    db: AsyncSession, bcd_id: str, user_id: str, user_feedback: str | None = None
) -> GenerationTarget:

    source = await get_bcd_or_404(db, bcd_id)

    if source.status == BCDStatus.GENERATING:
        raise GenerationAlreadyInProgress("Generation is already in progress.")

    result = await db.execute(select(BibleBook).where(BibleBook.id == source.book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise NotFoundError(f"Bible book for BCD {bcd_id} not found.")

    genre = (
        source.genre_context.get("primary_genre", "narrative")
        if source.genre_context
        else "narrative"
    )

    source_has_content = (
        source.structural_outline is not None or source.participant_register is not None
    )

    if not source_has_content:
        source.status = BCDStatus.GENERATING
        await db.commit()
        await db.refresh(source)
        target_bcd = source
    else:
        target_bcd = BookContextDocument(
            book_id=source.book_id,
            prepared_by=user_id,
            status=BCDStatus.GENERATING,
            version=source.version + 1,
            section_label=source.section_label,
            section_range_start=source.section_range_start,
            section_range_end=source.section_range_end,
            genre_context=source.genre_context,
        )
        db.add(target_bcd)
        await db.commit()
        await db.refresh(target_bcd)

    return GenerationTarget(
        target_bcd=target_bcd,
        book_name=book.name,
        genre=genre,
        chapter_count=book.chapter_count,
        user_feedback=user_feedback,
    )
