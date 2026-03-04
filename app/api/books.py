from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_app_access
from app.core.database import get_db
from app.models.meaning_map import (
    BibleBookResponse,
    ChapterSummary,
    PericopeWithStatusResponse,
)
from app.services import meaning_map_service

router = APIRouter()
_mm_access = require_app_access("meaning-map-generator")


@router.get("", response_model=list[BibleBookResponse], dependencies=[_mm_access])
async def list_books(
    db: AsyncSession = Depends(get_db),
) -> list[BibleBookResponse]:
    return await meaning_map_service.list_books(db)


@router.get("/dashboard-summary", dependencies=[_mm_access])
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await meaning_map_service.get_dashboard_summary(db)


@router.get("/{book_id}/chapters", response_model=list[ChapterSummary], dependencies=[_mm_access])
async def list_chapters(
    book_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ChapterSummary]:
    return await meaning_map_service.get_chapter_summaries(db, book_id)


@router.get(
    "/{book_id}/chapters/{chapter}/pericopes",
    response_model=list[PericopeWithStatusResponse],
    dependencies=[_mm_access],
)
async def list_chapter_pericopes(
    book_id: str,
    chapter: int,
    db: AsyncSession = Depends(get_db),
) -> list[PericopeWithStatusResponse]:
    return await meaning_map_service.list_pericopes(db, book_id, chapter)


@router.get(
    "/{book_id}/pericopes",
    response_model=list[PericopeWithStatusResponse],
    dependencies=[_mm_access],
)
async def list_book_pericopes(
    book_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[PericopeWithStatusResponse]:
    return await meaning_map_service.list_pericopes(db, book_id)
