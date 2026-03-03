from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError
from app.db.models.meaning_map import MeaningMap

VALID_TRANSITIONS = {
    ("draft", "cross_check"),
    ("cross_check", "approved"),
    ("cross_check", "draft"),
}


async def transition_status(
    db: AsyncSession, mm: MeaningMap, new_status: str, user_id: str
) -> MeaningMap:
    transition = (mm.status, new_status)
    if transition not in VALID_TRANSITIONS:
        raise ConflictError(f"Invalid status transition: {mm.status} -> {new_status}")

    if mm.locked_by and mm.locked_by != user_id:
        raise AuthorizationError("This meaning map is locked by another user")

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
    return mm
