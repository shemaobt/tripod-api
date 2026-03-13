from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification, NotificationMeaningMapDetail
from app.models.notification import NotificationResponse


async def enrich_with_details(
    db: AsyncSession,
    notifications: list[Notification],
) -> list[NotificationResponse]:

    if not notifications:
        return []

    notif_ids = [n.id for n in notifications]
    result = await db.execute(
        select(NotificationMeaningMapDetail).where(
            NotificationMeaningMapDetail.notification_id.in_(notif_ids)
        )
    )
    details_by_id = {d.notification_id: d for d in result.scalars().all()}

    responses = []
    for n in notifications:
        resp = NotificationResponse.model_validate(n)
        detail = details_by_id.get(n.id)
        if detail:
            resp.related_map_id = detail.related_map_id
            resp.pericope_reference = detail.pericope_reference
        responses.append(resp)
    return responses
