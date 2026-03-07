from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_app_access
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.meaning_map import PericopeCreate, PericopeResponse
from app.services import meaning_map_service
from app.services.book_context.has_approved import has_approved_bcd

router = APIRouter()
_mm_access = require_app_access("meaning-map-generator")


@router.post(
    "",
    response_model=PericopeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_mm_access],
)
async def create_pericope(
    payload: PericopeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PericopeResponse:
    book = await meaning_map_service.get_book_or_404(db, payload.book_id)
    meaning_map_service.ensure_ot(book)

    if not await has_approved_bcd(db, payload.book_id):
        raise HTTPException(
            status_code=409,
            detail="Book Context must be approved before adding pericopes.",
        )

    pericope = await meaning_map_service.create_pericope(
        db,
        book_id=payload.book_id,
        chapter_start=payload.chapter_start,
        verse_start=payload.verse_start,
        chapter_end=payload.chapter_end,
        verse_end=payload.verse_end,
        reference=payload.reference,
        title=payload.title,
    )
    return PericopeResponse.model_validate(pericope)
