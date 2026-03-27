from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import User
from app.db.models.book_context import BookContextDocument
from app.models.book_context import BCDListResponse, BCDResponse


async def _resolve_locked_by_name(db: AsyncSession, locked_by: str | None) -> str | None:
    if not locked_by:
        return None
    result = await db.execute(select(User.display_name).where(User.id == locked_by))
    return result.scalar_one_or_none()


async def enrich_bcd_response(db: AsyncSession, bcd: BookContextDocument) -> BCDResponse:
    resp = BCDResponse.model_validate(bcd)
    resp.locked_by_name = await _resolve_locked_by_name(db, bcd.locked_by)
    return resp


async def enrich_bcd_list_response(db: AsyncSession, bcd: BookContextDocument) -> BCDListResponse:
    resp = BCDListResponse.model_validate(bcd)
    resp.locked_by_name = await _resolve_locked_by_name(db, bcd.locked_by)
    return resp
