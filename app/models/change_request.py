from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChangeRequestCreate(BaseModel):
    kind: Literal["create_project", "create_language", "edit_language"]
    name: str | None = Field(default=None, max_length=200)
    code: str | None = Field(default=None, max_length=3)
    description: str | None = Field(default=None, max_length=10000)
    language_id: str | None = None


class ChangeRequestReview(BaseModel):
    status: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=2000)
    grant_manager_access: bool = False


class ChangeRequestResponse(BaseModel):
    id: str
    kind: str
    requester_user_id: str
    requester_display_name: str | None
    requester_email: str
    status: str
    name: str | None
    code: str | None
    description: str | None
    language_id: str | None
    grant_manager_access: bool
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_reason: str | None
    created_entity_id: str | None
    requested_at: datetime
