from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMapFeedback


async def add_feedback(
    db: AsyncSession,
    meaning_map_id: str,
    section_key: str,
    author_id: str,
    content: str,
) -> MeaningMapFeedback:
    fb = MeaningMapFeedback(
        meaning_map_id=meaning_map_id,
        section_key=section_key,
        author_id=author_id,
        content=content,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb
