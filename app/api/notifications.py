from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_app_access
from app.core.auth_middleware import get_current_user
from app.core.database import get_db
from app.db.models.auth import User
from app.models.notification import NotificationResponse, UnreadCountResponse
from app.services import notification_service

router = APIRouter()
_mm_access = require_app_access("meaning-map-generator")


@router.get("", response_model=list[NotificationResponse], dependencies=[_mm_access])
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationResponse]:
    app_id = await notification_service.get_mm_app_id(db)
    notifications = await notification_service.list_notifications(
        db, user.id, app_id, unread_only=unread_only, limit=limit
    )
    return await notification_service.enrich_with_details(db, notifications)


@router.get("/unread-count", response_model=UnreadCountResponse, dependencies=[_mm_access])
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    app_id = await notification_service.get_mm_app_id(db)
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
    enriched = await notification_service.enrich_with_details(db, [notif])
    return enriched[0]


@router.post("/mark-all-read", dependencies=[_mm_access])
async def mark_all_as_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    count = await notification_service.mark_all_as_read(db, user.id)
    return {"count": count}
