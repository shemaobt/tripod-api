from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError
from app.db.models.book_context import BCDApproval, BCDStatus, BookContextDocument
from app.services.book_context.get_bcd import get_bcd_or_404

ALLOWED_ROLES = frozenset({"admin"})


async def request_revision(
    db: AsyncSession,
    bcd_id: str,
    user_id: str,
    user_role: str,
) -> BookContextDocument:
    if user_role not in ALLOWED_ROLES:
        raise AuthorizationError("Only admins can request revisions.")

    bcd = await get_bcd_or_404(db, bcd_id)

    if bcd.status == BCDStatus.GENERATING:
        raise ConflictError("Cannot request revision on a document being generated.")

    await db.execute(delete(BCDApproval).where(BCDApproval.bcd_id == bcd_id))

    bcd.status = BCDStatus.DRAFT
    await db.commit()
    await db.refresh(bcd)
    return bcd
