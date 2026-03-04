from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_app_access
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import App, User
from app.db.models.notification import NotificationMeaningMapDetail
from app.models.notification import NotificationResponse, UnreadCountResponse
from app.services import notification_service

router = APIRouter()
_mm_access = require_app_access("meaning-map-generator")

MM_APP_KEY = "meaning-map-generator"


async def _get_app_id(db: AsyncSession) -> str:
    result = await db.execute(select(App.id).where(App.app_key == MM_APP_KEY))
    app_id = result.scalar_one_or_none()
    if app_id is None:
        raise RuntimeError(f"App '{MM_APP_KEY}' not found")
    return app_id


async def _enrich_with_details(
    db: AsyncSession, notifications: list,
) -> list[NotificationResponse]:
    """Build response list with meaning-map detail joined in."""
    if not notifications:
        return []

    notif_ids = [n.id for n in notifications]
    detail_stmt = select(NotificationMeaningMapDetail).where(
        NotificationMeaningMapDetail.notification_id.in_(notif_ids)
    )
    detail_result = await db.execute(detail_stmt)
    details_by_id = {d.notification_id: d for d in detail_result.scalars().all()}

    responses = []
    for n in notifications:
        resp = NotificationResponse.model_validate(n)
        detail = details_by_id.get(n.id)
        if detail:
            resp.related_map_id = detail.related_map_id
            resp.pericope_reference = detail.pericope_reference
        responses.append(resp)
    return responses


@router.get("", response_model=list[NotificationResponse], dependencies=[_mm_access])
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationResponse]:
    app_id = await _get_app_id(db)
    notifications = await notification_service.list_notifications(
        db, user.id, app_id, unread_only=unread_only, limit=limit
    )
    return await _enrich_with_details(db, notifications)


@router.get("/unread-count", response_model=UnreadCountResponse, dependencies=[_mm_access])
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    app_id = await _get_app_id(db)
    count = await notification_service.unread_count(db, user.id, app_id)
    return UnreadCountResponse(count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    dependencies=[_mm_access],
)
async def mark_as_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    notif = await notification_service.mark_as_read(db, notification_id, user.id)
    enriched = await _enrich_with_details(db, [notif])
    return enriched[0]


@router.post("/mark-all-read", dependencies=[_mm_access])
async def mark_all_as_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await notification_service.mark_all_as_read(db, user.id)
    return {"count": count}
