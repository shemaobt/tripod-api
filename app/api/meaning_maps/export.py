from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.meaning_maps._deps import mm_access
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.core.exceptions import AuthorizationError
from app.db.models.auth import User
from app.db.models.meaning_map import MeaningMapStatus
from app.services import meaning_map_service

router = APIRouter()


@router.get("/{map_id}/export/json", dependencies=[mm_access])
async def export_json(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    if mm.status != MeaningMapStatus.APPROVED:
        raise AuthorizationError("Only approved meaning maps can be exported")
    content = meaning_map_service.export_json(mm)
    return PlainTextResponse(content, media_type="application/json")


@router.get("/{map_id}/export/prose", dependencies=[mm_access])
async def export_prose(
    map_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    mm = await meaning_map_service.get_meaning_map_or_404(db, map_id)
    if mm.status != MeaningMapStatus.APPROVED:
        raise AuthorizationError("Only approved meaning maps can be exported")
    content = meaning_map_service.export_prose(mm)
    return PlainTextResponse(content, media_type="text/markdown")
