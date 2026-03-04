from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification, NotificationMeaningMapDetail


async def create_notification(
    db: AsyncSession,
    *,
    user_id: str,
    app_id: str,
    event_type: str,
    title: str,
    body: str,
    actor_id: str | None = None,
    related_map_id: str | None = None,
    pericope_reference: str | None = None,
) -> Notification:
    """Create a notification for a user within an app.

    If related_map_id or pericope_reference is provided, a child
    NotificationMeaningMapDetail row is also created.
    """
    notif = Notification(
        user_id=user_id,
        app_id=app_id,
        event_type=event_type,
        title=title,
        body=body,
        actor_id=actor_id,
    )
    db.add(notif)
    await db.flush()

    if related_map_id or pericope_reference:
        detail = NotificationMeaningMapDetail(
            notification_id=notif.id,
            related_map_id=related_map_id,
            pericope_reference=pericope_reference,
        )
        db.add(detail)

    await db.commit()
    await db.refresh(notif)
    return notif
