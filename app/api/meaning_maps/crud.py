from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.db.models.meaning_map import MeaningMap as MeaningMapModel
from app.models.meaning_map import (
    MeaningMapListResponse,
    MeaningMapResponse,
    MeaningMapStatusUpdate,
    MeaningMapUpdateData,
)
from app.services import meaning_map_service

from app.api.meaning_maps._deps import mm_access, mm_analyst

router = APIRouter()

async def _enrich(db: AsyncSession, mm: MeaningMapModel) -> MeaningMapResponse:
    return await meaning_map_service.enrich_meaning_map(db, mm)

@router.get("", response_model=list[MeaningMapListResponse], dependencies=[mm_access])
async def list_meaning_maps(
    book_id: str | None = Query(default=None),
    chapter: int | None = Query(default=None),
    map_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MeaningMapListResponse]:
    maps = await meaning_map_service.list_meaning_maps(
        db, book_id=book_id, chapter=chapter, status=map_status
    )
    return [MeaningMapListResponse.model_validate(m) for m in maps]

@router.get("/{map_id}", response_model=MeaningMapResponse, dependencies=[mm_access])
async def get_meaning_map(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    return await _enrich(db, mm)

@router.put("/{map_id}", response_model=MeaningMapResponse, dependencies=[mm_analyst])
async def update_meaning_map(
    map_id: str,
    payload: MeaningMapUpdateData,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm, book = await meaning_map_service.get_map_with_book(db, map_id)
    meaning_map_service.ensure_ot(book)
    mm = await meaning_map_service.update_meaning_map_data(db, mm, payload.data, user.id)
    return await _enrich(db, mm)

@router.patch("/{map_id}/status", response_model=MeaningMapResponse, dependencies=[mm_analyst])
async def update_status(
    map_id: str,
    payload: MeaningMapStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    mm = await meaning_map_service.transition_status(db, mm, payload.status, user.id)
    return await _enrich(db, mm)

@router.post("/{map_id}/lock", response_model=MeaningMapResponse, dependencies=[mm_analyst])
async def lock_map(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    mm = await meaning_map_service.lock_map(db, mm, user.id)
    return await _enrich(db, mm)

@router.post("/{map_id}/unlock", response_model=MeaningMapResponse, dependencies=[mm_analyst])
async def unlock_map(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeaningMapResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    mm = await meaning_map_service.unlock_map(db, mm, user.id, is_admin=user.is_platform_admin)
    return await _enrich(db, mm)

@router.delete("/{map_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[mm_analyst])
async def delete_meaning_map(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    await meaning_map_service.delete_meaning_map(db, mm, user.id)
