from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meaning_map import MeaningMap, MeaningMapFeedback, Pericope
from app.services.notifications.create_notification import create_notification
from app.services.notifications.get_mm_app_id import get_mm_app_id


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

    result = await db.execute(select(MeaningMap).where(MeaningMap.id == meaning_map_id))
    mm = result.scalar_one_or_none()
    if mm and mm.analyst_id != author_id:
        ref_result = await db.execute(
            select(Pericope.reference).where(Pericope.id == mm.pericope_id)
        )
        ref = ref_result.scalar_one_or_none() or "Unknown pericope"
        app_id = await get_mm_app_id(db)
        await create_notification(
            db,
            user_id=mm.analyst_id,
            app_id=app_id,
            event_type="feedback_added",
            title="New feedback on your meaning map",
            body=f"New feedback was added on your meaning map for {ref}.",
            actor_id=author_id,
            related_map_id=mm.id,
            pericope_reference=ref,
        )

    return fb
