from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.book_context import (
    PassageEntryBriefResponse,
    StalenessCheckResponse,
    ValidationIssue,
)
from app.services.book_context.check_stale import check_bcd_staleness
from app.services.book_context.compute_entry_brief import compute_entry_brief
from app.services.book_context.validate_against_brief import validate_map_against_brief
from app.services.meaning_map.get_meaning_map_or_404 import get_meaning_map_or_404

from app.api.book_context._deps import mm_access

router = APIRouter()

@router.get(
    "/entry-brief/{pericope_id}",
    response_model=PassageEntryBriefResponse,
    dependencies=[mm_access],
)
async def get_entry_brief(
    pericope_id: str,
    db: AsyncSession = Depends(get_db),
) -> PassageEntryBriefResponse:
    return await compute_entry_brief(db, pericope_id)

@router.get(
    "/staleness-check/{meaning_map_id}",
    response_model=StalenessCheckResponse,
    dependencies=[mm_access],
)
async def check_staleness(
    meaning_map_id: str,
    db: AsyncSession = Depends(get_db),
) -> StalenessCheckResponse:
    mm = await get_meaning_map_or_404(db, meaning_map_id)
    return await check_bcd_staleness(db, mm)

@router.get(
    "/validate/{meaning_map_id}",
    response_model=list[ValidationIssue],
    dependencies=[mm_access],
)
async def validate_meaning_map(
    meaning_map_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ValidationIssue]:
    mm = await get_meaning_map_or_404(db, meaning_map_id)
    return await validate_map_against_brief(db, mm)
