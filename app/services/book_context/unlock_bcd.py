from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.db.models.book_context import BookContextDocument


async def unlock_bcd(
    db: AsyncSession, bcd: BookContextDocument, user_id: str, *, is_admin: bool = False
) -> BookContextDocument:
    if not bcd.locked_by:
        return bcd
    if bcd.locked_by != user_id and not is_admin:
        raise AuthorizationError("Only the lock holder or an admin can unlock.")
    bcd.locked_by = None
    bcd.locked_at = None
    await db.commit()
    await db.refresh(bcd)
    return bcd
