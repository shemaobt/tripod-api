from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.book_context._deps import mm_access
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.book_context import BCDResponse, BCDSectionUpdateRequest
from app.services.book_context.enrich_bcd_response import enrich_bcd_response
from app.services.book_context.get_bcd import get_bcd_or_404
from app.services.book_context.lock_bcd import lock_bcd
from app.services.book_context.unlock_bcd import unlock_bcd
from app.services.book_context.update_section import update_section

router = APIRouter()


@router.patch(
    "/{bcd_id}/sections/{section_key}",
    response_model=BCDResponse,
    dependencies=[mm_access],
)
async def update_bcd_section(
    bcd_id: str,
    section_key: str,
    payload: BCDSectionUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await update_section(
        db, bcd_id, section_key, payload.data, user.id, locale=payload.locale
    )
    return await enrich_bcd_response(db, bcd)


@router.post(
    "/{bcd_id}/lock",
    response_model=BCDResponse,
    dependencies=[mm_access],
)
async def lock_bcd_endpoint(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await get_bcd_or_404(db, bcd_id)
    bcd = await lock_bcd(db, bcd, user.id)
    return await enrich_bcd_response(db, bcd)


@router.post(
    "/{bcd_id}/unlock",
    response_model=BCDResponse,
    dependencies=[mm_access],
)
async def unlock_bcd_endpoint(
    bcd_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await get_bcd_or_404(db, bcd_id)
    bcd = await unlock_bcd(db, bcd, user.id, is_admin=user.is_platform_admin)
    return await enrich_bcd_response(db, bcd)
