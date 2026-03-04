from datetime import datetime

from pydantic import BaseModel


class AccessRequestCreate(BaseModel):
    app_key: str
    note: str | None = None


class AccessRequestResponse(BaseModel):
    id: str
    user_id: str
    app_key: str
    status: str
    note: str | None
    requested_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_reason: str | None


class AccessRequestReviewRequest(BaseModel):
    status: str
    reason: str | None = None
