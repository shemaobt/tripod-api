from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    app_id: str
    event_type: str
    actor_id: str | None
    actor_name: str | None = None
    related_map_id: str | None = None
    pericope_reference: str | None = None
    title: str
    body: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    count: int
