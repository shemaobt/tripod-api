from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import Pericope


async def create_pericope(
    db: AsyncSession,
    book_id: str,
    chapter_start: int,
    verse_start: int,
    chapter_end: int,
    verse_end: int,
    reference: str,
    title: str | None = None,
) -> Pericope:
    pericope = Pericope(
        book_id=book_id,
        chapter_start=chapter_start,
        verse_start=verse_start,
        chapter_end=chapter_end,
        verse_end=verse_end,
        reference=reference,
        title=title,
    )
    db.add(pericope)
    await db.commit()
    await db.refresh(pericope)
    return pericope
