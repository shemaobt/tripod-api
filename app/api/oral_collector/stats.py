from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_middleware import get_current_user, require_platform_admin
from app.core.database import get_db
from app.db.models.auth import User
from app.models.oc_stats import AdminStatsResponse, GenreStatsResponse
from app.services.oral_collector import stats_service

stats_router = APIRouter()

@stats_router.get(
    "/projects/{project_id}/genre-stats",
    response_model=GenreStatsResponse,
)
async def get_genre_stats(
    project_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenreStatsResponse:

    stats = await stats_service.get_genre_stats(db, project_id)
    return GenreStatsResponse(**stats)

@stats_router.get(
    "/admin/stats",
    response_model=AdminStatsResponse,
)
async def get_admin_stats(
    _: User = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminStatsResponse:

    stats = await stats_service.get_admin_stats(db)
    return AdminStatsResponse(**stats)
