from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.book_context import BCDResponse, BCDSectionUpdateRequest
from app.services.book_context.update_section import update_section

from app.api.book_context._deps import mm_access

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
    bcd = await update_section(db, bcd_id, section_key, payload.data)
    return BCDResponse.model_validate(bcd)
