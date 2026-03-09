from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError
from app.db.models.meaning_map import MeaningMap, Pericope
from app.services.notifications.create_notification import create_notification
from app.services.notifications.get_mm_app_id import get_mm_app_id

VALID_TRANSITIONS = {
    ("draft", "cross_check"),
    ("cross_check", "approved"),
    ("cross_check", "draft"),
}


async def _get_pericope_reference(db: AsyncSession, pericope_id: str) -> str:
    result = await db.execute(select(Pericope.reference).where(Pericope.id == pericope_id))
    return result.scalar_one_or_none() or "Unknown pericope"


async def transition_status(
    db: AsyncSession, mm: MeaningMap, new_status: str, user_id: str
) -> MeaningMap:
    transition = (mm.status, new_status)
    if transition not in VALID_TRANSITIONS:
        raise ConflictError(f"Invalid status transition: {mm.status} -> {new_status}")

    if mm.locked_by and mm.locked_by != user_id:
        raise AuthorizationError("This meaning map is locked by another user")

    is_cross_check = transition in (
        ("cross_check", "approved"),
        ("cross_check", "draft"),
    )
    if is_cross_check and mm.analyst_id == user_id:
        raise AuthorizationError("You cannot cross-check your own meaning map")

    if transition == ("draft", "cross_check"):
        mm.status = "cross_check"
        mm.locked_by = None
        mm.locked_at = None

    elif transition == ("cross_check", "approved"):
        mm.status = "approved"
        mm.date_approved = datetime.now(UTC)
        mm.approved_by = user_id
        mm.cross_checker_id = user_id
        mm.locked_by = None
        mm.locked_at = None

    elif transition == ("cross_check", "draft"):
        mm.status = "draft"
        mm.locked_by = None
        mm.locked_at = None

    await db.commit()
    await db.refresh(mm)

    if transition == ("cross_check", "approved"):
        ref = await _get_pericope_reference(db, mm.pericope_id)
        app_id = await get_mm_app_id(db)
        await create_notification(
            db,
            user_id=mm.analyst_id,
            app_id=app_id,
            event_type="map_approved",
            title="Your meaning map was approved",
            body=f"Your meaning map for {ref} has been approved.",
            actor_id=user_id,
            related_map_id=mm.id,
            pericope_reference=ref,
        )

    elif transition == ("cross_check", "draft"):
        ref = await _get_pericope_reference(db, mm.pericope_id)
        app_id = await get_mm_app_id(db)
        await create_notification(
            db,
            user_id=mm.analyst_id,
            app_id=app_id,
            event_type="revisions_requested",
            title="Revisions requested on your meaning map",
            body=f"Revisions have been requested on your meaning map for {ref}.",
            actor_id=user_id,
            related_map_id=mm.id,
            pericope_reference=ref,
        )

    return mm
