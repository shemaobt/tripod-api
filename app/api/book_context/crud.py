from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.book_context._deps import mm_access
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.book_context import (
    BCDApprovalStatusResponse,
    BCDCreateRequest,
    BCDListResponse,
    BCDResponse,
)
from app.services.book_context.create_bcd import create_bcd
from app.services.book_context.enrich_bcd_response import (
    enrich_bcd_list_response,
    enrich_bcd_response,
)
from app.services.book_context.get_approval_status import get_approval_status
from app.services.book_context.get_bcd import get_bcd_or_404
from app.services.book_context.list_bcds import list_bcds

router = APIRouter()


@router.get("", response_model=list[BCDListResponse], dependencies=[mm_access])
async def list_book_context_documents(
    book_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[BCDListResponse]:
    items = await list_bcds(db, book_id=book_id)
    return [await enrich_bcd_list_response(db, bcd) for bcd in items]


@router.post(
    "/{book_id}",
    response_model=BCDResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[mm_access],
)
async def create_book_context_document(
    book_id: str,
    payload: BCDCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await create_bcd(
        db,
        book_id,
        user.id,
        payload.genre,
        section_label=payload.section_label,
        section_range_start=payload.section_range_start,
        section_range_end=payload.section_range_end,
    )
    return await enrich_bcd_response(db, bcd)


@router.get("/{bcd_id}", response_model=BCDResponse, dependencies=[mm_access])
async def get_book_context_document(
    bcd_id: str,
    db: AsyncSession = Depends(get_db),
) -> BCDResponse:
    bcd = await get_bcd_or_404(db, bcd_id)
    return await enrich_bcd_response(db, bcd)


@router.get(
    "/{bcd_id}/approval-status",
    response_model=BCDApprovalStatusResponse,
    dependencies=[mm_access],
)
async def get_bcd_approval_status(
    bcd_id: str,
    db: AsyncSession = Depends(get_db),
) -> BCDApprovalStatusResponse:
    return await get_approval_status(db, bcd_id)
