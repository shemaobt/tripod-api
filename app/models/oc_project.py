from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class OCProjectUserResponse(BaseModel):
    project_id: str
    user_id: str
    role: str
    joined_at: datetime
    invited_by: str | None

    model_config = {"from_attributes": True}


class OCProjectInviteCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="user", max_length=30)


class OCProjectInviteResponse(BaseModel):
    id: str
    project_id: str
    email: str
    invited_by: str
    status: str
    role: str
    created_at: datetime
    accepted_at: datetime | None

    model_config = {"from_attributes": True}
